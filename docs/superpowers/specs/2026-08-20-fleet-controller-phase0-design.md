# Fleet Controller — Phase 0 Design

## Context & Constraints

- Background: a 5-idea infra roadmap ("serious sci-fi infra plan") proposed
  combining idea #1 (mission-director / mission graphs) and idea #5
  (HyperBrain-style skill/memory routing) into one autonomous orchestration
  layer. Explicitly **not** literal AGI (the source doc's own header: "we
  wont AGI BROski") — the goal is safe increasing autonomy with hard
  containment, not general intelligence.
- Three architectures for the mission-director/executor split were weighed.
  **Approach C** (hard separation — the planner has zero mutation authority,
  a deterministic controller has zero LLM) was chosen over (A) one service
  that both plans and checks its own permission, and (B) bolting LLM
  planning onto HyperFlow's existing deterministic goal-matcher. The
  governing rule: **no component may both interpret LLM output and possess
  infrastructure mutation authority.**
- This is a 5+ phase project (prove the boundary → typed dispatch → signed
  verdicts → human approval → one live action → infrastructure mutation).
  **This spec covers only Phase 0.** `mission-director` (the LLM planner),
  capability tokens, and any live execution are documented as future phases,
  not built here — see Out of Scope.
- Ground-truth findings from a live repo audit (2026-08-20), used to correct
  the original proposal against what's actually in the codebase:
  - `agents/crew-orchestrator/safety_gate.py`'s `evaluate_dispatch()` fails
    **open** on any Safety Shepherd error/timeout/unreachable — returns
    `{"decision": "ALLOW", "skipped": True}`. This is deliberate, documented
    behavior for its actual use case: routine task dispatch ("a dead sidecar
    must not stop the crew"), with 3 live callers (crew-orchestrator itself,
    `hyperflow_runner.py`, `coder-studio/shepherd.py`).
  - `fleet-controller` is a brand-new, separate container. It cannot import
    crew-orchestrator's Python module — this repo has no cross-agent
    package-import convention; agents share code by file-copy (e.g.
    `base_agent.py` is copied into each agent's own directory), never by
    importing another agent's package at runtime. So fleet-controller never
    routes through the existing fail-open path at all — it gets its own
    client code, written fail-closed from day one.
  - **Scope decision**: Phase 0 does **not** modify `safety_gate.py`. Its
    fail-open behavior is a separate, deliberate design choice for a
    different use case with 3 live callers — changing shared behavior for
    those callers is its own decision (logged below as a follow-up finding),
    not something Phase 0 needs to touch to prove its own containment
    property.
  - Safety Shepherd's real `/evaluate` (`agents/safety-shepherd/safety_shepherd.py:335`,
    request shape `EvaluateRequest` at `:231`) already accepts
    `category: "docker"` — one of the existing `DANGEROUS` categories
    (`policy.py:33`) that already default to `ESCALATE` without an explicit
    capability grant (`policy.py`, precedence rule 9). **Phase 0 needs zero
    changes to Safety Shepherd itself** — fleet-controller calls the
    existing, unmodified endpoint.
  - Governance Ledger's `POST /api/v1/governance/ledger`
    (`backend/app/api/v1/endpoints/governance.py`) already has a free-form
    `payload: dict` column — plan hash, mission id, and decision fit today
    with zero schema migration.
  - `hypercode-core` (and therefore the Governance Ledger endpoint it hosts)
    is reachable on `agents-net` — confirmed via `docker inspect`. No
    `data-net` membership needed for fleet-controller.

## Goal

Prove, mechanically — not just by policy — that a new `fleet-controller`
service can accept a typed infrastructure-change proposal, validate it, ask
Safety Shepherd, and produce a preview, while being **structurally
incapable of executing anything**: no Docker socket, no `DOCKER_HOST`, no
crew-orchestrator dispatch credentials, no LLM/MCP/GitHub-write access. If
Safety Shepherd is unreachable or returns something unexpected, the result
is always `BLOCK`, never a silent `ALLOW`.

## Design

### 1. New service: `agents/fleet-controller/`

Same shape as every other agent in this repo — own Dockerfile, non-root
user, `HEALTHCHECK` curling `/health`, `AGENT_PORT=8080` baked in (matching
the item-#9 port convention) — but deliberately minimal:

```
agents/fleet-controller/
├── Dockerfile
├── requirements.txt      # fastapi, uvicorn, httpx, pydantic — nothing else
├── main.py               # FastAPI app: /health, /v1/plans/preview
├── models.py             # PlanRequest / PlanResponse pydantic models
├── plan_validator.py     # schema + allowlist checks, before Shepherd is ever called
├── safety_client.py      # fail-closed Safety Shepherd client (§4)
└── tests/
    ├── test_validation.py
    ├── test_hashing.py
    ├── test_safety_unavailable.py
    └── test_no_execution.py
```

No `docker` package in `requirements.txt`. No `anthropic`/`openai` — no LLM
client exists in this process at all (`mission-director` is a later,
separate service). No MCP tooling.

### 2. Plan schema (`models.py`)

```python
class RequestedAction(BaseModel):
    action_id: str
    kind: Literal["compose_profile.preview", "crew.workflow.preview"]
    profile: str | None = None

class Constraints(BaseModel):
    max_services: int = 25
    allow_profiles: list[str] = []
    deny_profiles: list[str] = []

class PlanRequest(BaseModel):
    schema_version: Literal[1]
    mission_id: str
    requested_actions: list[RequestedAction]
    constraints: Constraints
```

Phase 0's `kind` allowlist is exactly two values. No `start`/`stop`/`build`/
`exec`/`rm`/`prune`/`migrate`/`dispatch` action kinds exist in the schema at
all — pydantic's `Literal` rejects anything else at the wire level, before
any handler code runs.

### 3. `plan_validator.py` — reject before ever contacting Shepherd

Rejects with `422` (never reaches `safety_client.py`):

- missing or wrong `schema_version`
- empty `requested_actions`
- duplicate `action_id`
- unknown `kind` (enforced by the `Literal` type itself)
- `profile` not in `constraints.allow_profiles`, or present in
  `constraints.deny_profiles`
- `profile in {"prod", "gpu"}` — hard-denied regardless of what the
  caller's own `constraints` claim, so a client can't bypass it by simply
  omitting `deny_profiles`

### 4. `safety_client.py` — fail-closed by construction

```python
@dataclass(frozen=True)
class SafetyResult:
    decision: str                 # ALLOW | BLOCK | ESCALATE
    reason: str
    rule: str | None = None
    category: str | None = None
    shepherd_available: bool = True
    fail_closed: bool = False

async def check_infrastructure_mutation(plan: PlanRequest, plan_hash: str) -> SafetyResult:
    ...
```

Every non-2xx response, timeout, connection error, malformed JSON, or
response missing a `decision` field returns:

```python
SafetyResult(
    decision="BLOCK",
    reason="Safety Shepherd unavailable; fail-closed",
    shepherd_available=False,
    fail_closed=True,
)
```

There is no `mode` concept here (no `off`/`monitor`, unlike
`evaluate_dispatch`) — this path is unconditionally enforced. A component
whose entire job is proving a safety boundary has no "monitor mode" that
makes sense. Calls Safety Shepherd's existing, unmodified `/evaluate` with
`category="docker"` — already in Shepherd's `DANGEROUS` set, so it already
defaults to `ESCALATE` without a capability grant. No Shepherd-side changes
needed.

### 5. `POST /v1/plans/preview`

Request: a `PlanRequest` (§2). Response:

```json
{
  "plan_id": "plan_...",
  "plan_hash": "sha256:...",
  "mode": "DRY_RUN",
  "safety": {
    "decision": "BLOCK",
    "reason": "Safety Shepherd unavailable; fail-closed",
    "shepherd_available": false
  },
  "execution": {
    "performed": false,
    "would_execute": []
  }
}
```

`execution.performed` is `false` in every response Phase 0 can ever
produce — there is no code path that sets it to `true`; no Docker client
exists in the process to execute anything with.

`plan_hash = sha256(canonical_json(plan))`, canonicalized (sorted keys, no
whitespace) so it's stable regardless of field order and changes the
instant any field changes — tamper-evidence proven by test now, enforced by
signing in Phase 2.

### 6. Durable proposal record

Every preview call writes one row to the existing Governance Ledger
(`POST /api/v1/governance/ledger`, unmodified) — `agent="fleet-controller"`,
`action="plan.preview"`, `decision=<safety.decision>`,
`payload={mission_id, plan_id, plan_hash, requested_actions, safety_reason,
performed: false}`. No new table, no migration — `payload` is already a
free-form JSON column.

### 7. Compose wiring — the boundary has to be true at the infrastructure level too

New profile, `fleet`. The service:

- connects to `agents-net` only (confirmed sufficient — `hypercode-core`,
  hosting the Governance Ledger endpoint, is reachable there; no `data-net`
  needed)
- **does not** mount `/var/run/docker.sock`
- **does not** set `DOCKER_HOST`
- **does not** receive `ORCHESTRATOR_API_KEY` or any crew-orchestrator
  credential
- `depends_on: safety-shepherd: condition: service_started` — Phase 0 must
  work *correctly because* Shepherd might be down, not assume it's always up

Which existing compose file hosts this new service (extend
`docker-compose.agents-full.yml`, or a new `docker-compose.fleet.yml`) is
left to the implementation plan.

## API Behaviour Summary

| Scenario | `safety.decision` | `execution.performed` |
|---|---|---|
| Valid plan, Shepherd reachable, ALLOW | `ALLOW` | `false` |
| Valid plan, Shepherd reachable, BLOCK | `BLOCK` | `false` |
| Valid plan, Shepherd reachable, ESCALATE | `ESCALATE` | `false` |
| Shepherd timeout / unreachable | `BLOCK` (`shepherd_available=false`) | `false` |
| Shepherd returns malformed JSON / missing `decision` | `BLOCK` (`shepherd_available=false`) | `false` |
| Unknown action `kind` | `422` before Shepherd is ever called | — |
| `profile in {"prod", "gpu"}` | `422` before Shepherd is ever called | — |
| Plan modified after hashing | `plan_hash` changes (proven by test; not cryptographically enforced until Phase 2 signing) | — |

## Error Handling

Every failure mode — bad schema, denied profile, Shepherd down, Shepherd
malformed — resolves to either a `422` (rejected before Shepherd is
contacted) or a `200` with `safety.decision != ALLOW` and
`execution.performed = false`. There is no code path in Phase 0 capable of
setting `performed = true`. "Fail safe" isn't a runtime check to get right
here — it's a structural fact about what the service is capable of doing.

## Testing Plan

- `test_validation.py` — every `plan_validator.py` rejection rule (§3), one
  test per rule.
- `test_hashing.py` — `canonical_hash(plan)` changes when any field
  changes; identical for reordered-but-equal dicts.
- `test_safety_unavailable.py` — mocked timeout, connection error,
  non-200, malformed JSON, missing `decision` field: all five assert
  `decision == "BLOCK"` and `shepherd_available == False`.
- `test_no_execution.py` — for every scenario above (including Shepherd
  `ALLOW`), assert `execution.performed is False` and a mocked "would
  dispatch to Docker" callable is never invoked.
- CI negative-capability check (added to the existing
  `docker-push.yml`/`health-check.yml`, not a new workflow):
  `docker inspect fleet-controller --format '{{json .Config.Env}}' | grep -E 'DOCKER_HOST|ANTHROPIC_API_KEY|GITHUB_TOKEN'`
  must find nothing; `docker compose config` for the `fleet-controller`
  service must show no `docker.sock` in `volumes`. Both assert on the
  *rendered deployment manifest*, not just the code — the architecture is
  only real if the manifest proves it too.

## Out of Scope (future phases, documented not built)

- `mission-director` (the LLM planner) — Phase 1+. Has zero mutation
  authority regardless of when it's built, per the governing rule.
- Capability tokens / cryptographic signing of verdicts — Phase 2. The
  response schema reserves a `"capability": null` field so it fits later,
  but nothing issues or verifies one yet. (A JWT library is already a repo
  dependency, used for dashboard sessions — Phase 2 extends that, doesn't
  start from scratch.)
- Live execution of any kind (`compose_profile.start`, crew dispatch) —
  Phase 4/5, gated behind Phase 0–3 passing plus explicit two-person-rule
  approval for the `DRY_RUN`→`LIVE` switch. Phase 4 starts with the
  lowest-risk live action (crew plan submission), not Docker profile
  flipping.
- Fixing `crew-orchestrator/safety_gate.py`'s fail-open behavior for its 3
  existing task-dispatch callers. Real, pre-existing, deliberately out of
  scope here — fleet-controller never routes through it, and changing
  shared behavior for 3 live callers (crew-orchestrator,
  `hyperflow_runner.py`, `coder-studio/shepherd.py`) is its own decision
  with its own compatibility analysis, not something to bundle into this
  spec.
- Investigating `workflow_engine.py`'s `/workflow/execute` as the eventual
  target for "crew plan submission" — needed before Phase 4 designs that
  integration, not before Phase 0. `crew-orchestrator` currently has no
  multi-step plan-submission endpoint at all (`/execute` takes one task).
- The three-plane model (cognitive / governance / execution), extending
  `brain-agent` into a capability-recommender for "who should own this
  task," and Safety Shepherd's richer verdict schema
  (`risk_class`/`allowed_actions`/`policy_version`) beyond today's plain
  `{decision, reason, rule, category}` — all documented in this session's
  design discussion as the target shape, none built yet.

## Rollout Order

1. Scaffold `agents/fleet-controller/` (Dockerfile, requirements, empty
   FastAPI app with `/health`) — matches every other agent's build/port/
   healthcheck convention.
2. `models.py` + `plan_validator.py` + `test_validation.py`.
3. `canonical_hash()` + `test_hashing.py`.
4. `safety_client.py` (fail-closed) + `test_safety_unavailable.py` — the
   one that matters most; get it right before anything else touches it.
5. `POST /v1/plans/preview` wiring it all together + `test_no_execution.py`.
6. Governance Ledger write on every preview call.
7. Compose wiring (`fleet` profile, network/env/`depends_on` per §7) + the
   CI negative-capability checks.
8. Manual smoke test: one valid plan with Shepherd up, one with Shepherd
   killed mid-request, one with a denied profile — confirm all three land
   exactly where the API Behaviour Summary table says.
