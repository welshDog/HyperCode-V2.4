# Track 2: Policy-Aware Crew Orchestrator

This doc describes the **Policy Engine** and **Agent Registry** that turn HyperCode's crew orchestrator into a policy‑aware, governance‑capable system.

## Overview

Track 2 adds:

- **Agent Registry** — a table of known agents with roles, locations, trust scores, and allowed data domains.
- **Policy Rules** — a priority‑ordered list of conditions → actions (allow/deny/require_approval).
- **Audit Log** — a tamper‑evident log of every policy decision, with chained hashes.
- **Policy Engine** — a Python service that evaluates agent actions against rules and writes audit entries.

This aligns with the "Security Module" in [ARCHITECTURE_OS.md](ARCHITECTURE_OS.md) and the Multi‑Agent Orchestration Protocol pattern of a central orchestrator + policy engine + audit log.[web:7]

## Database Schema

Three new tables (migration `010_agent_policy_schema.py`):

### `agent_registry`

| Column | Type | Description |
|--------|------|-------------|
| `id` | uuid | Primary key. |
| `name` | text | Unique agent name (e.g. `healer`, `coder-agent`, `pet-chat`). |
| `role` | text | Role (e.g. `healer`, `orchestrator`, `specialist`). |
| `location` | text | Deployment island: `local`, `edge`, `cloud`. |
| `trust_score` | int | 0–100 trust score. |
| `allowed_data_domains` | jsonb | List of allowed domains, e.g. `["users", "token_transactions"]`. |
| `capabilities` | jsonb | List of capabilities, e.g. `["read_users", "write_tokens"]`. |
| `created_at` | timestamptz | Creation timestamp. |
| `updated_at` | timestamptz | Last update timestamp. |

### `policy_rules`

| Column | Type | Description |
|--------|------|-------------|
| `id` | uuid | Primary key. |
| `name` | text | Unique rule name. |
| `description` | text | Human-readable description. |
| `condition` | jsonb | Condition object (see below). |
| `action` | text | `allow`, `deny`, or `require_approval`. |
| `priority` | int | Higher = evaluated first. |
| `enabled` | bool | Whether the rule is active. |
| `created_at` | timestamptz | Creation timestamp. |
| `updated_at` | timestamptz | Last update timestamp. |

**Condition shape:**

```json
{
  "field": "data_domain",
  "op": "in",
  "value": ["users", "token_transactions"]
}
```

Supported ops: `eq`, `ne`, `in`, `not_in`, `exists`.

Fields: `data_domain`, `action`, `agent_id`, `task_id`.

### `audit_log`

| Column | Type | Description |
|--------|------|-------------|
| `id` | uuid | Primary key. |
| `timestamp` | timestamptz | Event timestamp. |
| `agent_id` | uuid | Reference to `agent_registry.id`. |
| `task_id` | text | Optional task identifier. |
| `action` | text | Action attempted (e.g. `award_tokens`). |
| `data_domain` | text | Data domain accessed (e.g. `token_transactions`). |
| `policy_result` | text | `allowed`, `denied`, `pending_approval`. |
| `details` | jsonb | Optional structured details. |
| `hash_prev` | text | Hash of previous audit row (for tamper evidence). |
| `hash_self` | text | SHA256 of this row's key fields + `hash_prev`. |

The `hash_prev` / `hash_self` chain makes it computationally expensive to alter history without detection.

## Policy Engine API

Located at `backend/app/services/policy_engine.py`.

### Core types

```python
@dataclass
class PolicyCheck:
    agent_id: Optional[str]
    task_id: Optional[str]
    action: str
    data_domain: Optional[str]
    details: Optional[Dict[str, Any]] = None

@dataclass
class PolicyDecision:
    result: PolicyResult  # ALLOWED, DENIED, PENDING_APPROVAL
    matched_rule_name: Optional[str]
    reason: str
```

### Usage pattern

```python
from app.services.policy_engine import PolicyEngine, PolicyCheck, create_policy_engine
from asyncpg import create_pool

async def main():
    db_pool = await create_pool(DATABASE_URL)
    engine = await create_policy_engine(db_pool)

    check = PolicyCheck(
        agent_id="some-uuid",
        task_id="task-123",
        action="award_tokens",
        data_domain="token_transactions",
        details={"amount": 50, "reason": "Completed lesson 1"},
    )

    decision = await engine.evaluate(check)
    await engine.log_decision(check, decision)

    if decision.result == "allowed":
        # proceed with action
        ...
    else:
        # deny or require approval
        ...
```

## Example Policy Rules

Here are example rules you might insert:

```sql
-- 1. Only trusted local agents can touch token transactions
INSERT INTO policy_rules (name, description, condition, action, priority, enabled)
VALUES (
  'local_trusted_tokens',
  'Allow only local agents with trust >= 70 to access token_transactions',
  '{"field": "data_domain", "op": "eq", "value": "token_transactions"}',
  'allow',
  100,
  true
);

-- 2. Deny cloud agents from accessing users table
INSERT INTO policy_rules (name, description, condition, action, priority, enabled)
VALUES (
  'no_cloud_users',
  'Deny any agent with location=cloud from accessing users',
  '{"field": "data_domain", "op": "eq", "value": "users"}',
  'deny',
  90,
  true
);

-- 3. Require approval for high-value token awards
INSERT INTO policy_rules (name, description, condition, action, priority, enabled)
VALUES (
  'approve_large_awards',
  'Require approval for award_tokens with amount > 1000',
  '{"field": "action", "op": "eq", "value": "award_tokens"}',
  'require_approval',
  80,
  true
);
```

In a fuller implementation, you'd add more granular conditions (e.g. on `details.amount`) and tie `location` to the `agent_registry`.

## Wiring into the Crew Orchestrator

To integrate this with the existing crew orchestrator:

1. **Initialize the policy engine** at app startup alongside the DB pool.
2. **Before dispatching a task** to an agent, construct a `PolicyCheck` with:
   - `agent_id` (from `agent_registry`)
   - `task_id`
   - `action` (e.g. `award_tokens`, `create_checkout`)
   - `data_domain` (e.g. `token_transactions`, `stripe_payments`)
3. **Call `engine.evaluate(check)`** and inspect `decision.result`:
   - `ALLOWED` → proceed with dispatch.
   - `DENIED` → reject task, log, and optionally notify.
   - `PENDING_APPROVAL` → queue for human/lead approval before dispatch.
4. **Always call `engine.log_decision(check, decision)`** to record the decision in `audit_log`.

This turns every agent action into a policy‑checked, auditable event.

## Neurodivergent‑First Policy Design

The policy engine can encode neurodivergent‑friendly constraints:

- **Focus mode policies** — e.g. "no non‑critical notifications during focus sessions".
- **Privacy boundaries** — e.g. "pet chat can only read `users.discord_id` and `broski_tokens`".
- **Island rules** — e.g. "token ops must stay on Local Island".

These become explicit, testable rules instead of ad‑hoc assumptions.

## Next Steps

Future enhancements:

- Add a small admin UI or CLI to manage `policy_rules` and view `audit_log`.
- Extend condition language (e.g. numeric comparisons on `details.amount`).
- Integrate with the orchestrator's existing task dispatch logic.
- Add Prometheus metrics for policy decisions (allow/deny rates, pending approvals).

## References

- Multi‑Agent Orchestration Protocol research (policy engine + audit log pattern).[web:7]
- HyperCode OS architecture: [ARCHITECTURE_OS.md](ARCHITECTURE_OS.md).
