# Mission Director — Phase 1 Design

## Context & Constraints

- Continues the fleet-controller Phase 0 roadmap
  (`docs/superpowers/specs/2026-08-20-fleet-controller-phase0-design.md`),
  which proved a containment boundary exists and named its own future
  phases without building them: "`mission-director` (the LLM planner)...
  documented as future phases, not built here." This spec covers only
  that Phase 1.
- Governing rule, unchanged from Phase 0: **no component may both interpret
  LLM output and possess infrastructure mutation authority.**
  Mission-director interprets LLM output and has zero mutation authority.
  fleet-controller will eventually gain bounded mutation authority (Phase 3+)
  and interprets no LLM output at all — the split holds across the boundary
  this spec adds.
- Ground-truth findings from reading the real, live code this session (not
  assumed):
  - `agents/fleet-controller/models.py`'s `PlanRequest` already accepts a
    `mission_id: str`, `requested_actions: list[RequestedAction]`, and
    `constraints: Constraints`, with a canonical `plan_hash` via
    `canonical_hash()`. **Phase 1 needs zero changes to fleet-controller** —
    mission-director's entire job is producing a valid `PlanRequest` and
    calling the `/v1/plans/preview` endpoint that already exists and is
    already smoke-tested (`docs/superpowers/specs/2026-08-20-fleet-controller-phase0-design.md`'s
    live-verification section).
  - `agents/fleet-controller/main.py`'s `POST /v1/plans/preview` has **no
    authentication at all** — containment there comes from capability
    absence (no Docker socket, no LLM client, no mutation code path), not
    access control. Mission-director's client needs no credential to reach
    it beyond network access.
  - `backend/app/api/v1/endpoints/governance.py` already has both auth
    patterns Phase 1 needs, ready to reuse directly: `deps.get_current_active_user`
    (user-JWT, human) gates `GET /ledger`; `require_agent_key` (`X-Agent-Key`,
    machine) gates `POST /ledger`. Phase 1's two new human-facing endpoints
    reuse `get_current_active_user` — no new auth plumbing.
  - Specialist agents (`agents/*/base_agent.py`) already build a real
    `AsyncAnthropic` client (`ANTHROPIC_API_KEY`, Ollama fallback) for actual
    LLM calls — mission-director's LLM client reuses this pattern, not a new
    one.
  - `agents/crew-orchestrator/crew_v2.py` is a real, unused CrewAI
    hierarchical planner with an Opus/Sonnet/Haiku tier map. Not adopted in
    Phase 1 (see Out of Scope) — its existence is noted so it isn't
    rediscovered and re-litigated later without this context.
  - `:8097` is a free host port — every published port in
    `docker-compose.agents.yml` + `docker-compose.agents-full.yml` was
    grepped this session; `:8095`/`:8096` are taken
    (`hyperhealth-api`/`safety-shepherd`), `:8097` is free since
    `session-snapshot` moved off it 2026-08-20.
  - `docs/superpowers/specs/2026-08-21-fleet-truth-registry-design.md`
    (spec'd, not yet implemented) is where `truth_snapshot_ref` comes from.
    **Phase 1 depends on that registry being built, not just spec'd** — see
    Rollout Order.

## Goal

A safe, end-to-end proof that a human-submitted goal can become a previewed,
audited, human-reviewable plan — with zero possibility of live mutation
anywhere in the path, and zero new fleet-controller surface area. Success
looks like fleet-controller's own Phase 0 bar: every failure mode (bad LLM
output, fleet-controller unreachable, no truth snapshot available) fails
closed and is provably distinguishable from a real, reviewable proposal.

## Non-Goals (this spec)

- Capability tokens / signed verdicts (Phase 2).
- Any live execution (Phase 3+).
- A dashboard/UI for human review beyond the raw API — Phase 0 also shipped
  API-only; a review surface is a separable, later concern.
- The mission evaluator (Phase 4).
- Self-triggered or autonomous mission creation, ever, in this lineage,
  without its own explicit, separately-approved decision — Phase 1's
  `propose` endpoint is human-authed specifically to make this structurally
  true, not just documented policy.
- Adopting `crew_v2.py` wholesale. It's noted as a candidate reference for
  Phase 1's plan-generation prompt/tier design, but Phase 1 builds its own
  minimal LLM-call path scoped to the `MissionProposal` schema — importing
  CrewAI's full `Process.hierarchical` machinery would pull in far more
  surface area (multi-agent delegation, tool use) than a single
  goal-to-typed-plan call needs.

## Design

### 1. New service: `agents/mission-director/`

Layout mirrors `agents/fleet-controller/`, with one addition that
fleet-controller didn't need — `mission_store.py` (see §6, Durable mission
record):

```
agents/mission-director/
  main.py            # FastAPI app, 3 routes: /health, /v1/missions/propose, /v1/missions/{id}/review
  models.py           # MissionProposal, ReviewDecision, state machine
  plan_generator.py   # LLM call -> MissionProposal, forced schema validation
  local_validator.py  # fast, non-safety well-formedness checks
  fleet_client.py      # thin httpx client for fleet-controller's /v1/plans/preview
  mission_store.py     # mission_proposals table: create/get-by-id/update-status
  ledger_client.py     # fire-and-forget, mirrors fleet-controller's own ledger_client.py pattern
  Dockerfile
  requirements.txt
  tests/
    conftest.py
    test_validation.py
    test_no_execution.py
    test_llm_malformed_output.py
    test_fleet_controller_unavailable.py
```

### 2. `MissionProposal` schema (`models.py`)

```python
from fleet_controller_models import PlanRequest  # vendored copy, same file-copy
                                                    # convention every agent uses
                                                    # (no cross-agent package imports
                                                    # in this repo)

class MissionProposal(BaseModel):
    schema_version: Literal[1]
    mission_id: str
    goal: str                              # verbatim human input, never LLM-rewritten
    truth_snapshot_ref: str                 # hash/version from the truth registry
    rationale: str                          # LLM's reasoning — advisory, never validated as fact
    plan: PlanRequest                       # fleet-controller's real, unmodified schema
    status: Literal[
        "proposed", "previewed", "approved", "rejected",
        "preview_unavailable", "rejected_malformed",
    ]
    superseded_from: Optional[str] = None   # set only when resubmitting after a terminal failure
```

**State machine — status is server-controlled, never client-settable:**

| From | To | Set by | Trigger |
|---|---|---|---|
| (none) | `proposed` | `plan_generator.py` | LLM call succeeds, output validates against `MissionProposal` |
| (none) | `rejected_malformed` | `plan_generator.py` | LLM output fails schema validation — terminal, no retry loop |
| `proposed` | `previewed` | `fleet_client.py` | fleet-controller returns *any* `PlanResponse` — including a BLOCK/ESCALATE verdict, which still counts as a successful preview |
| `proposed` | `preview_unavailable` | `fleet_client.py` | fleet-controller unreachable, non-200, or malformed response — terminal |
| `previewed` | `approved` / `rejected` | `POST /v1/missions/{id}/review` | human decision only, via `get_current_active_user` |

No request body may set `status` directly — it's derived server-side at every
step. A `MissionProposal` is never mutated after creation; a resubmission
after a terminal failure state (`preview_unavailable`, `rejected_malformed`,
or `rejected`) creates a **new** proposal with a new `mission_id` and
`superseded_from` pointing at the old one.

### 3. Local validation (`local_validator.py`)

Runs after the LLM call, before any network call to fleet-controller:
- Schema already enforced by pydantic (unknown/missing fields reject at
  the wire level, same as fleet-controller's closed `Literal` set does for
  `RequestedAction.kind`).
- `plan.requested_actions` non-empty.
- `truth_snapshot_ref` present and non-empty.

This is explicitly **not** a safety decision — it's a fast, deterministic
well-formedness gate to avoid spending a network round-trip on garbage.
Every actual safety judgment (dangerous categories, profile denials) stays
exactly where it already lives: `plan_validator.py` and Safety Shepherd's
`policy.py`, both inside fleet-controller's boundary, both untouched by
this spec.

### 4. `POST /v1/missions/propose`

Request: `{"goal": str}`. Auth: `Depends(deps.get_current_active_user)` —
reused directly from `governance.py`, not reimplemented. This is what makes
"human-submitted only, no self-triggering" a structural fact, not a
documented convention: no agent identity can call this route at all.

Flow: read the current truth-registry snapshot (`build()` from
`docs/superpowers/specs/2026-08-21-fleet-truth-registry-design.md`'s
`fleet_registry.py`, once built) → call Claude via the shared
`AsyncAnthropic` pattern, forcing tool-use/structured output into
`MissionProposal`'s shape → on schema failure, return `status:
rejected_malformed` immediately, no retry → run local validation → if it
fails, same `rejected_malformed` terminal state → POST `plan` to
fleet-controller's existing `/v1/plans/preview`, unmodified → on network/
non-200/malformed-response failure, `status: preview_unavailable` → on
success, `status: previewed`, store the `PlanResponse` alongside the
proposal → write the full record to the Governance Ledger → return the
`MissionProposal` (including fleet-controller's safety verdict) to the
caller.

If the truth registry itself is unavailable (compose files unreadable,
overlay validation fails), mission-director fails closed the same way:
`status: preview_unavailable` before ever calling fleet-controller or the
LLM — never plans against an absent or unverified world model.

### 5. `POST /v1/missions/{id}/review`

Request: `{"decision": "approve" | "reject"}`. Auth: same
`get_current_active_user` dependency. Valid only when the mission's current
`status` is `previewed` — any other current status returns 409, not a
silent no-op. Writes the decision + reviewer identity to the Governance
Ledger. **Approving performs nothing live** — there is no code path in
Phase 1, anywhere in `mission-director` or in the unmodified
`fleet-controller`, that can set `PlanResponse.execution.performed = True`.
Approval only advances `MissionProposal.status`; it does not call anything.

### 6. Durable mission record — new table, unlike fleet-controller

fleet-controller's Phase 0 needed no persistence of its own ("no new
table, no migration") because every request is a single, complete,
stateless round-trip — there is no later call that needs to look anything
up. Mission-director's `review` endpoint breaks that: it arrives in a
**separate** HTTP request from `propose` and must find the right
proposal by `mission_id`, then enforce `status == previewed` before
accepting a decision. The Governance Ledger's `payload` column is
free-form JSON with no indexed query support for that lookup — reusing it
as the only store would mean scanning ledger history to reconstruct
current state on every review call, which is fragile and unnecessarily
slow for what's a simple point-lookup problem.

So Phase 1 adds one small table, `mission_proposals` (`mission_id` PK,
`status`, `goal`, `truth_snapshot_ref`, `plan` JSONB, `plan_response`
JSONB, `superseded_from`, `created_at`, `updated_at`) — mission-director's
own operational current-state store, analogous to how other services in
this ecosystem (e.g. Mission Control's `mc_missions`) keep their own state
table alongside writing to a separate audit log. This table is **not** a
replacement for the Governance Ledger — it's what makes point-lookups and
precondition checks possible; the Ledger stays the permanent, append-only
audit trail.

### 7. Governance Ledger record shape

One ledger write per terminal event (mirrors fleet-controller's own
`ledger_client.py` fire-and-forget pattern, not a new client): the full
`MissionProposal` (goal, rationale, plan, truth_snapshot_ref), the
`PlanResponse` fleet-controller returned (safety verdict, plan_hash,
execution view), and — once a review happens — the decision and the
reviewing user's identity. This is the same "what was known / what was
proposed / what was approved / what happened" evidence chain the fleet
truth-registry review named as the real success metric for this whole
roadmap.

### 8. Compose wiring

New service block in `docker-compose.agents-full.yml`, `container_name:
mission-director`, `"127.0.0.1:8097:8080"`, `profiles: ["fleet"]` — the
same profile as fleet-controller, not a new one, since this is a matched
pair and there's no reason to fragment the opt-in boundary further. No
`depends_on: crew-orchestrator: condition: service_healthy` — the same
named exception fleet-controller already has and for the same reason
(mission-director has no crew-orchestrator credential and no dispatch path
through it). New: also no `depends_on: safety-shepherd` — unlike
fleet-controller, mission-director never talks to Shepherd directly (see
below), so it has no direct dependency on it at all, only a transitive one
through fleet-controller.

### 9. Explicit exception: no Safety Shepherd client

Named and confirmed here, mirroring how fleet-controller's own
crew-orchestrator exception was asked and confirmed before building, not a
silent gap: **mission-director holds no Safety Shepherd credential and
makes no direct call to Shepherd's `/evaluate`.** Only fleet-controller
talks to Shepherd. This keeps the safety-evaluation responsibility in
exactly one place instead of letting it spread as the pipeline grows a new
component.

## API Behaviour Summary

| Endpoint | Auth | Precondition | Result |
|---|---|---|---|
| `POST /v1/missions/propose` | user-JWT | none | `previewed` (success), `rejected_malformed` (bad LLM output or failed local validation), `preview_unavailable` (fleet-controller or truth registry unreachable) |
| `POST /v1/missions/{id}/review` | user-JWT | `status == previewed` | `approved` / `rejected`; 409 if status is anything else |
| `GET /health` | none | — | liveness only, matches every other agent's convention |

## Error Handling

| Failure | Behaviour |
|---|---|
| Truth registry unavailable/invalid | `preview_unavailable`, before any LLM or fleet-controller call |
| LLM call fails outright (timeout, API error) | `preview_unavailable` — treated as an infrastructure failure, not a plan-quality failure |
| LLM responds but output fails schema validation | `rejected_malformed` — never coerced, never auto-retried |
| Local validation fails (empty actions, missing snapshot ref) | `rejected_malformed` |
| fleet-controller unreachable / non-200 / malformed response | `preview_unavailable` |
| fleet-controller returns a valid `PlanResponse` (any safety verdict) | `previewed` — this is success for mission-director's purposes; the verdict itself is for the human reviewer to read |
| Review attempted when status isn't `previewed` | 409, ledger untouched |
| Ledger write fails | Fire-and-forget, matches fleet-controller's existing `ledger_client.py` — logged, never blocks the response to the caller |

## Testing Plan

Mirrors `agents/fleet-controller/tests/` exactly in style (plain pytest, no
unittest classes, a `conftest.py` fixture for the FastAPI test client via
`httpx.ASGITransport`):

- `test_validation.py` — schema acceptance/rejection for `MissionProposal`
  and each state transition table row.
- `test_no_execution.py` — asserts no code path in the module can ever set
  an execution/mutation flag `True`; asserts `approve` never triggers any
  outbound call beyond the Ledger write.
- `test_llm_malformed_output.py` — mocks the LLM client returning
  non-conforming output, asserts `rejected_malformed`, asserts no
  fleet-controller call was made.
- `test_fleet_controller_unavailable.py` — mocks a fleet-controller
  connection failure, asserts `preview_unavailable`, asserts the proposal
  is still recorded to the Ledger (a failed attempt is still evidence).

## Out of Scope (future phases, documented not built)

See Non-Goals above — capability tokens, live execution, the evaluator, a
review UI, and `crew_v2.py` adoption are all explicitly deferred, not
silently dropped.

## Rollout Order

1. **Truth registry implementation** (`docs/superpowers/specs/2026-08-21-fleet-truth-registry-design.md`)
   — must land first. `truth_snapshot_ref` is not optional plumbing; it's
   the reason this phase exists.
2. `mission_proposals` table migration via the existing `backend/alembic/`
   setup (same database `hypercode-core`/Governance Ledger already use, no
   new database instance, no new migration tool) + `mission_store.py`,
   tested standalone against a real DB before anything else depends on it.
3. `agents/mission-director/` scaffold + `models.py` + tests, verified
   standalone (`docker build` + `docker run` + `curl /health`, same bar
   Phase 0 used) before any compose wiring.
4. Wire `POST /v1/missions/propose` against a **real** fleet-controller
   instance (not a mock) — confirm a real `PlanResponse` round-trips
   correctly, including a real ESCALATE/BLOCK verdict, not just the happy
   path.
5. Wire `POST /v1/missions/{id}/review` + Ledger recording.
6. Compose wiring behind `--profile fleet`, swept against the live stack
   (zero unhealthy containers before and after, same as every prior fleet
   change this session).
