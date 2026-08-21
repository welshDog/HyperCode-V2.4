# Mission Evaluator — Design

## Context & Constraints

- Continues the pipeline named in the fleet-controller Phase 0 spec's
  future-phases section and `HYPERCODE_V3_ROADMAP.md`'s diagram: "mission
  evaluator — watches every run above, compares intended vs. actual
  outcome, safety events, cost, human corrections, rollback quality →
  structured lessons. **Not a second executor.**"
- **Scope correction made during brainstorming, before any code was
  written**: the roadmap frames the evaluator as Phase 4, coming *after*
  Phase 2 (capability tokens) and Phase 3 (bounded live execution). Its
  full vision — comparing intended vs. *actual* outcome, cost, rollback
  quality — needs real execution data that doesn't exist yet:
  `mission-director` Phase 1's `review` endpoint is explicit that
  "approving performs nothing live." This spec covers a **narrower v1**:
  evaluate what already exists today (proposal quality + the human
  review decision), forward-compatible with real outcome data once
  Phase 3 lands, but shipping now rather than waiting on it.
- Governing rule, unchanged from every prior phase: **no component may
  both interpret LLM output and possess infrastructure mutation
  authority.** The evaluator interprets nothing an LLM produced in real
  time — it reads already-recorded `mission_proposals` rows after the
  fact — and has zero mutation authority over anything but its own new
  table. It is a pure observer, matching the roadmap's own "not a second
  executor" framing literally: it has no execution code path at all, not
  even a disabled one.
- Ground-truth findings from reading the real, live code this session
  (not assumed):
  - `backend/app/models/mission.py`'s `MissionProposal` (table
    `mission_proposals`, from Mission Director Phase 1) already has
    every field this spec needs: `mission_id`, `status`, `goal`,
    `truth_snapshot_ref`, `plan` (JSONB), `plan_response` (JSONB),
    `superseded_from`, `created_at`, `updated_at`. **Zero changes needed
    to that table or model.**
  - `agents/mission-director/models.py`'s `PlanResponse` (the shape
    stored in `plan_response`) has `safety: {decision, reason, rule,
    category, shepherd_available}` and `execution: {performed,
    would_execute}`. `plan_response` is `null` on `rejected_malformed`/
    `preview_unavailable` rows (no fleet-controller call was ever made
    or it failed) — the evaluator must handle a null `plan_response`
    without erroring, not assume it's always present.
  - `backend/app/api/v1/endpoints/missions.py`'s `review_mission`
    (Phase 1) gates only on `row.status == "previewed"` — it never reads
    or re-checks `plan_response.safety.decision` before allowing an
    `approve`. **Confirmed by reading the live code, not assumed.** This
    means a human can currently approve a mission that fleet-controller's
    own Safety Shepherd verdict was `BLOCK` for. Today this is harmless
    (approval triggers no execution anywhere), but it's exactly the kind
    of gap worth surfacing before a later phase gives "approved" real
    teeth — this is the evaluator's flagship check, not a hypothetical.
  - `backend/app/api/api.py` already has the exact "conditionally
    imported router" pattern this spec's new endpoint follows —
    mirroring `_HAS_GOVERNANCE`/`_HAS_MISSIONS` precisely, since this
    also needs a new model/migration.
  - `backend/tests/conftest.py`'s `db`/`client` fixtures (in-memory
    SQLite, `Base.metadata.create_all()`) are the same test infrastructure
    Mission Director Phase 1's tests already use — no new test scaffolding
    needed.

## Goal

Turn the existing `mission_proposals` audit trail into structured,
queryable "lessons" about how well the propose→review pipeline is
actually working — without executing anything, without calling an LLM,
and without adding any new mutation capability anywhere in the system.

Success looks like: a human can query one endpoint and get a real answer
to "how well is mission-director doing" — proposal validity rate, human
agreement/disagreement with Shepherd's safety verdict, and a hard flag on
the one existing anomaly class that matters most (approved-despite-BLOCK).

## Non-Goals (this spec)

- LLM-graded rationale/plan quality (deferred — the roadmap's own Phase
  5 note already says LLM-capability improvements are "evaluated
  case-by-case with real evidence once there's a live system generating
  it, not adopted upfront as speculative architecture." An MVP grading
  LLM output with another LLM call is exactly that speculative
  complexity.)
- Comparing intended vs. *actual* execution outcome, cost, or rollback
  quality — none of that data exists until Phase 3 (bounded live
  execution) ships. This spec evaluates proposal-and-review quality only.
- Any feedback loop that changes mission-director's prompts, behavior, or
  future plan generation based on evaluation results. Pure observer, no
  adaptation, ever, in this spec.
- Scheduling/cron automation of evaluation runs — on-demand only.
- Evaluating `previewed` (pending-review) missions — only missions that
  reached a terminal state are evaluable; a pending mission has no
  review decision yet to evaluate.
- A dashboard/UI — API-only, matching every prior phase's own scoping
  (Phase 0 and Phase 1 both shipped API-only; a review/reporting surface
  is a separable, later concern each time it's come up).

## Design

### 1. New table: `mission_evaluations`

One row per evaluated mission (`mission_id` is unique — a mission is
evaluated once; re-running `POST /run` skips missions that already have
a row, never re-evaluates or overwrites).

```
mission_evaluations
  mission_id        TEXT PK — references mission_proposals.mission_id
                     (no FK constraint enforced at the DB level — mirrors
                     mission_proposals' own relationship to
                     governance_ledger, a soft reference by convention,
                     not a hard foreign key, so evaluation logic never
                     blocks on referential integrity machinery). One row
                     per mission, same PK-is-a-meaningful-string
                     convention mission_proposals itself already uses —
                     no separate synthetic id needed.
  verdict           TEXT — "clean" | "anomaly"
  checks            JSONB — structured per-check results, see §2
  summary           TEXT — one human-readable sentence, e.g. "approved
                     despite BLOCK verdict" or "clean: rejected_malformed"
  evaluated_at       TIMESTAMPTZ, server_default now()
```

Index on `verdict` (mirrors `mission_proposals`' own `ix_..._status`
index — the summary endpoint's most common query is "how many
anomalies").

### 2. `checks` JSONB shape (the actual rule logic)

Computed once per mission from its `mission_proposals` row alone — no
other table read, no network call, no LLM call:

```json
{
  "status": "approved",
  "plan_malformed": false,
  "preview_failed": false,
  "safety_decision": "BLOCK",
  "human_decision": "approved",
  "anomaly_approved_despite_block": true,
  "anomaly_rejected_despite_allow": false
}
```

Rule definitions, in the order they're computed:
- `status`: the mission's own `mission_proposals.status` value, copied
  verbatim.
- `plan_malformed`: `status == "rejected_malformed"`.
- `preview_failed`: `status == "preview_unavailable"`.
- `safety_decision`: `plan_response["safety"]["decision"]` if
  `plan_response` is not null, else `null`. Read defensively
  (`.get(...)` chains) — a present-but-malformed `plan_response` (should
  never happen per Mission Director Phase 1's own validation, but the
  evaluator doesn't trust upstream data blindly either) degrades to
  `null`, never raises.
- `human_decision`: `"approved"` if `status == "approved"`, `"rejected"`
  if `status == "rejected"`, else `null` (a mission that never reached
  review — `rejected_malformed`/`preview_unavailable` — has no human
  decision to record).
- `anomaly_approved_despite_block`: `human_decision == "approved" and
  safety_decision == "BLOCK"`. **The flagship check** — see Context.
- `anomaly_rejected_despite_allow`: `human_decision == "rejected" and
  safety_decision == "ALLOW"`. Secondary, lower-priority signal (a human
  being more cautious than Shepherd isn't dangerous — just worth
  counting, e.g. to notice if humans are rejecting things for reasons
  Shepherd's policy doesn't capture).

`verdict` is `"anomaly"` if either anomaly flag is `true`, else
`"clean"`. `summary` is generated from whichever flags are set — a
short, fixed-template sentence per case (not free text, not LLM-written
— deterministic string formatting from the `checks` dict).

### 3. Evaluable missions

A mission is evaluable if its `status` is one of `rejected_malformed`,
`preview_unavailable`, `approved`, `rejected` — the four terminal
states. `previewed` (awaiting review) and any future non-terminal status
are never evaluated.

### 4. `POST /api/v1/mission-evaluations/run`

Auth: `Depends(deps.get_current_active_user)` — same dependency, same
process, zero reimplementation, matching every other human-facing
backend endpoint in this repo (`missions.py`'s `propose`/`review`,
`governance.py`'s `GET /ledger`).

Flow: query `mission_proposals` for rows whose `status` is one of the
four terminal states AND whose `mission_id` has no existing row in
`mission_evaluations` → for each, compute `checks`/`verdict`/`summary`
per §2 → insert one `mission_evaluations` row per mission (one DB
transaction per mission, not one giant transaction for the whole batch —
so a failure partway through a large backlog still leaves earlier
missions evaluated, not rolled back) → return a run summary.

Response:
```json
{
  "evaluated_count": 12,
  "anomaly_count": 1,
  "already_evaluated_skipped": 3
}
```

Idempotent by construction: calling `run` twice in a row with no new
terminal missions in between evaluates zero new rows the second time
(the "already evaluated" skip, not an error).

### 5. `GET /api/v1/mission-evaluations`

Auth: same dependency. Query params: `verdict` (optional filter,
`"clean"`/`"anomaly"`), `limit`/`offset` (pagination, same convention as
`governance.py`'s `GET /ledger`: `limit` default 50 max 500, `offset`
default 0). Returns `{"total": int, "count": int, "rows": [...]}`, same
shape as `GET /ledger`'s own response — one serialized `mission_evaluations`
row per entry (`mission_id`, `verdict`, `checks`, `summary`,
`evaluated_at`).

### 6. `GET /api/v1/mission-evaluations/summary`

Auth: same dependency. Aggregate rollup computed from every row in
`mission_evaluations` (no pagination — this is a small table, one row
per mission, and the whole point is a single-glance answer):

```json
{
  "total_evaluated": 12,
  "plan_malformed_rate": 0.083,
  "preview_failed_rate": 0.25,
  "human_approved_count": 6,
  "human_rejected_count": 2,
  "anomaly_approved_despite_block_count": 1,
  "anomaly_rejected_despite_allow_count": 0
}
```

All rates are `count / total_evaluated`, `0.0` if `total_evaluated == 0`
(never a division-by-zero error).

### 7. New backend files

```
backend/app/models/mission_evaluation.py   # MissionEvaluation SQLAlchemy model
backend/app/services/mission_evaluator.py   # pure rule logic: evaluate_mission(proposal) -> dict
backend/app/services/mission_evaluation_store.py  # create/list/summary CRUD
backend/app/api/v1/endpoints/mission_evaluations.py  # 3 routes
backend/alembic/versions/021_add_mission_evaluations.py  # new migration, down_revision="020"
```

`mission_evaluator.py`'s `evaluate_mission(proposal: MissionProposal) ->
dict` is a pure function — no DB access, no network call — taking a
`MissionProposal` ORM object (or anything with the same 4 relevant
attributes: `status`, `plan_response`) and returning the `checks` dict
from §2 plus `verdict`/`summary`. This is what makes it trivially unit
testable without a DB at all, and keeps the actual rule logic in one
small, focused file separate from persistence/HTTP concerns — same
separation-of-concerns pattern `local_validator.py` used in Mission
Director Phase 1.

## API Behaviour Summary

| Endpoint | Auth | Result |
|---|---|---|
| `POST /mission-evaluations/run` | user-JWT | Evaluates all unevaluated terminal missions, returns a run summary. Idempotent. |
| `GET /mission-evaluations` | user-JWT | Paginated list, filterable by verdict. |
| `GET /mission-evaluations/summary` | user-JWT | Aggregate rollup, single-glance rates + anomaly counts. |

## Error Handling

| Failure | Behaviour |
|---|---|
| `plan_response` is null on a terminal mission | `safety_decision` computed as `null`, no error — `rejected_malformed`/`preview_unavailable` missions never had a fleet-controller response to read. |
| `plan_response` present but missing expected keys | Defensive `.get(...)` access, `safety_decision` defaults to `null` rather than raising. |
| `run` called with zero new terminal missions | Returns `{"evaluated_count": 0, "anomaly_count": 0, "already_evaluated_skipped": N}` — success, not an error. |
| One mission's evaluation fails unexpectedly mid-batch | Per-mission transaction means earlier successes in the same `run` call are already committed; the failure surfaces as a 500 for that call, next `run` call picks up where it left off (failed mission has no row yet, so it's retried). |

## Testing Plan

Mirrors Mission Director Phase 1's own testing style (plain pytest, real
DB fixture from `backend/tests/conftest.py`, no unittest classes):

- `backend/tests/test_mission_evaluator.py` — pure unit tests for
  `evaluate_mission()`, no DB: each of the 4 terminal statuses, a null
  `plan_response`, each anomaly flag firing/not-firing, verdict/summary
  derivation.
- `backend/tests/test_mission_evaluation_store.py` — CRUD against the
  real (test) DB: create, list with verdict filter, summary rates
  including the zero-total case.
- `backend/tests/test_mission_evaluations_endpoint.py` — HTTP-level:
  auth required on all 3 routes (mirrors
  `test_missions_endpoint.py`'s `test_propose_requires_auth`/
  `test_review_requires_auth` pattern), `run` evaluates real seeded
  `mission_proposals` rows and skips already-evaluated ones on a second
  call, `run` correctly flags the approved-despite-BLOCK case using a
  seeded row with that exact combination, `summary` returns correct
  rates against a small seeded set including the zero-total case.

## Out of Scope (future phases, documented not built)

See Non-Goals above — LLM-graded quality, real execution-outcome
comparison (Phase 3-dependent), any adaptive feedback loop, scheduling,
and a dashboard UI are all explicitly deferred, not silently dropped.
Once Phase 3 (bounded live execution) exists, this spec's `checks`
JSONB shape is designed to extend (not redesign) — new keys added
alongside the existing ones, `mission_evaluations` stays the same table.

## Rollout Order

1. `mission_evaluations` table migration + model, tested standalone
   against a real DB before anything else depends on it.
2. `mission_evaluator.py`'s pure rule logic + unit tests — no DB, no
   HTTP, verified in isolation first (matches Mission Director Phase
   1's own "scaffold + tests, verified standalone" precedent).
3. `mission_evaluation_store.py` + its tests, against a real DB.
4. The 3 HTTP routes + router registration + endpoint-level tests.
5. Live verification against the real running stack: seed or use the
   real `mission_proposals` rows already created during Mission Director
   Phase 1's own live verification (at least one real `preview_unavailable`
   row already exists from that session), call `POST /run`, confirm the
   response and a real `GET /summary` result.
