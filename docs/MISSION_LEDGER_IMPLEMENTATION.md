# Mission Ledger — Implementation Complete ✅

## What Was Built

### 1. Database Schema (Supabase)
**File:** `supabase/migrations/20260904095600_create_mission_ledger.sql`

Three tables:
- **missions** — Core mission tracking (goal, builder, branch, PR, status, next_action)
- **mission_events** — Audit trail of all state changes
- **mission_proof** — Evidence: lint, tests, security scans, Playwright, deployments

Key features:
- Auto-generated mission IDs: `HC-2026-09-001`, `HC-2026-09-002`, etc.
- Row Level Security (RLS) policies
- Auto-updating `updated_at` timestamp
- Check constraints on status, event_type, proof_type

### 2. Python Client
**File:** `agents/mission-ledger/ledger_client.py`

`MissionLedger` class with methods:
- `create_mission(goal, builder, context_pack, metadata)`
- `get_mission(mission_id)`
- `update_mission(mission_id, **fields)`
- `list_missions(status, builder, limit)`
- `record_event(mission_id, event_type, event_data)`
- `attach_proof(mission_id, proof_type, status, result_json, artifact_url)`
- `get_mission_with_proof(mission_id)` — Returns mission + proof summary
- `start_mission(mission_id, branch)` — Convenience: sets status=in_progress
- `complete_mission(mission_id, pr_url, pr_number, preview_url)` — Convenience: sets status=awaiting_review
- `fail_mission(mission_id, error)` — Convenience: sets status=failed

### 3. Specification Doc
**File:** `docs/MISSION_LEDGER_SPEC.md`

Full API spec, schema documentation, integration points, security model.

---

## How to Use

### Step 1: Run the migration

In your Supabase dashboard SQL editor or via CLI:

```bash
supabase db push
```

Or paste the contents of `supabase/migrations/20260904095600_create_mission_ledger.sql` into the Supabase SQL editor.

### Step 2: Set environment variables

```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your-service-role-key"
```

### Step 3: Use in your agents

```python
from agents.mission-ledger.ledger_client import MissionLedger

ledger = MissionLedger()

# Create a mission
mission = ledger.create_mission(
    goal="Add secure Vercel preview deployment flow",
    builder="claude-code",
    context_pack={
        "related_issues": ["#123"],
        "acceptance_criteria": ["Preview deploys on PR"]
    }
)

print(f"Mission created: {mission['mission_id']}")

# Start the mission
mission = ledger.start_mission(mission['mission_id'], "feat/vercel-preview")

# Attach proof as work completes
ledger.attach_proof(
    mission['mission_id'],
    proof_type="lint",
    status="passed",
    result_json={"errors": 0, "warnings": 2}
)

ledger.attach_proof(
    mission['mission_id'],
    proof_type="tests",
    status="passed",
    result_json={"total": 42, "passed": 42}
)

# Complete the mission
mission = ledger.complete_mission(
    mission['mission_id'],
    pr_url="https://github.com/welshDog/HyperCode-V2.4/pull/453",
    pr_number=453,
    preview_url="https://hypercode-v2-4.vercel.app"
)

# Get full mission with proof
full = ledger.get_mission_with_proof(mission['mission_id'])
print(f"Proof: {full['proof']}")
print(f"Next action: {full['next_action']}")
```

---

## Integration Points

### Mission Director (`agents/mission-director/main.py`)
```python
from agents.mission-ledger.ledger_client import MissionLedger

ledger = MissionLedger()

# In your plan generator:
mission = ledger.create_mission(
    goal=user_goal,
    builder="claude-code",
    context_pack=plan.context
)

# After Claude Code completes work:
mission = ledger.complete_mission(
    mission['mission_id'],
    pr_url=pr.html_url,
    pr_number=pr.number,
    preview_url=preview_url
)
```

### Crew Orchestrator (`agents/crew-orchestrator/main.py`)
```python
# Attach proof as tasks complete:
ledger.attach_proof(
    mission_id,
    proof_type="tests",
    status="passed" if tests_passed else "failed",
    result_json=test_results
)

ledger.attach_proof(
    mission_id,
    proof_type="security_scan",
    status="passed" if no_vulns else "failed",
    result_json=scan_results
)
```

### Healer (`agents/healer/main.py`)
```python
# Monitor mission health:
if mission_age > timeout:
    ledger.fail_mission(mission_id, error="Mission timed out")

# Trigger rollback on failure:
ledger.attach_proof(
    mission_id,
    proof_type="rollback",
    status="passed",
    result_json={"rollback_commit": rollback_sha}
)
```

---

## Next Steps

### 1. Integrate with Mission Director
Update `agents/mission-director/main.py` to use `MissionLedger` instead of in-memory state.

### 2. Add Proof Attachment to Crew Orchestrator
Wire `ledger.attach_proof()` into the Crew workflow after each task completes.

### 3. Build Dashboard View
Create a simple web UI or CLI command to view missions:

```bash
hyper missions list --status awaiting_review
hyper missions show HC-2026-09-001
```

### 4. Add to PR Template
Auto-fill `.github/PULL_REQUEST_TEMPLATE.md` with mission data:

```markdown
## Mission
- **ID**: {{ mission_id }}
- **Goal**: {{ goal }}
- **Proof**: {{ proof_summary }}
- **Next Action**: {{ next_action }}
```

---

## Security Notes

- **RLS Policies** — Currently allow all authenticated users full access. Tighten based on your auth setup.
- **Service Key** — Use service role key for server-side code, anon key for client-side with stricter RLS.
- **Sensitive Data** — Never store tokens, passwords, or secrets in mission metadata. Use Supabase vault or environment variables.

---

**BROski♾ — Mission Ledger foundation locked in.** Ready to integrate! 🔥
