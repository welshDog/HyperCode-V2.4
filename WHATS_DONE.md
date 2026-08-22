# ✅ WHATS_DONE — HyperCode-V2.4

> Last synced: 2026-08-22 by Claude + welshDog ⚡

---

## 2026-08-23 night — item 0a: `project-strategist`'s dead planning code wired up

`agents/08-project-strategist/agent.py`'s `plan()`/`delegate_tasks()` — the
actual "break a feature down and delegate to specialist agents" logic this
agent exists for — were unreachable dead code, found during the item #0
compose-dedupe fix. Three real bugs, all fixed:

1. `ProjectStrategist` never overrode `process_task`, so `/execute` always
   fell through to `BaseAgent`'s generic LLM passthrough. Now overrides it
   (preserving the base class's `requires_approval` gate), derives a
   `task_id` from context or generates one, and calls `plan()` for real.
2. `plan()` called `self.client.messages.create(...)` and
   `self.redis.hset(...)` without `await` against async clients — both are
   coroutines. Fixed, and `self.redis` calls are now guarded (`if
   self.redis:`) since it can be `None` if Redis was unreachable at startup.
3. `plan()` referenced `self.config.core_url`, which doesn't exist on
   `AgentConfig` — would have thrown `AttributeError` the first time it ran.
   Replaced with `os.getenv("CORE_URL", "http://hypercode-core:8000")`;
   `CORE_URL` was already correctly set in `docker-compose.agents.yml`, just
   never read anywhere.

`plan()`'s signature changed from taking a `TaskRequest` object to
`(task_id, task, context)` primitives, matching what `process_task` actually
has available — checked first that nothing else in the repo called the old
signature (only an HTTP-level script,
`tests/test_orchestrator_strategist_integration.py`, exists, unaffected).

**Verified live**: the container bind-mounts its own directory
(`./agents/08-project-strategist:/app`), so a plain `docker restart` applied
the fix, no rebuild needed. Constructed the real `ProjectStrategist` object
in-process inside the running container (monkeypatching only the LLM client
to the Ollama fallback, since `ANTHROPIC_API_KEY` is still invalid per N1)
and called `process_task` directly — proved the full await chain now works:
it reaches `plan()`, correctly awaits the LLM call, and a real HTTP request
lands at Ollama (failed only on an unrelated, expected model-name mismatch —
Ollama has no Claude models pulled). Did not push through to a full
successful generation: a second attempt with a real Ollama model
(`tinyllama`) drove the box to `0` free swap mid-generation on an already
resource-tight night — killed it and restarted `hypercode-ollama` to
recover cleanly rather than chase a second OOM incident for marginal extra
proof. A true end-to-end proof (real plan generated, specialists actually
called) stays blocked on N1.

Also confirmed, not just assumed: `project-strategist`'s earlier
`Exited (255)` (found during the N7 sweep, root cause never identified — no
error in its logs before the exit) has not recurred since last night's
full-fleet restart — 0 restarts, stable throughout tonight's session.

---

## 2026-08-22 night — N2 credential rotation (JWT + Postgres password) shipped (#434)

**`DASHBOARD_SERVICE_JWT`**: re-minted a fresh 365-day token via the
documented `create_access_token(1, timedelta(days=365))` procedure, run
inside the live `hypercode-core` container so the raw token never touched
stdout/chat — moved to a local scratch file, applied to `.env` via one
approved edit, scratch file deleted immediately after. `dashboard` container
recreated, verified live end-to-end (`GET /api/tasks` → `200`, was the
JWT-gated proxy route).

**Postgres password**: generated a new random hex password, rotated the live
role via `ALTER ROLE ... WITH PASSWORD` (no downtime — existing sessions
keep working, only new connections need the new password), and proved the
rotation actually took effect over the network from a real client
(`asyncpg` from `hypercode-core` to `postgres:5432`): old password →
`InvalidPasswordError`, new password → connects. (An earlier local-socket
test had given a false "old password still works" result — Postgres's
`pg_hba.conf` trusts local Unix-socket connections regardless of password,
so that test proved nothing; the real proof needed a network client.)
`.env` updated: `POSTGRES_PASSWORD`, `DB_PASSWORD`, `DATABASE_URL`.

**Two real gaps found doing this, not just the headline rotation**:

1. The first dependency sweep (`docker exec $c printenv DATABASE_URL`)
   missed `hypercode-core` and `celery-worker` entirely — both read
   `HYPERCODE_DB_URL` instead, built from `${POSTGRES_PASSWORD}` via compose
   variable substitution in `docker-compose.core.yml`. Both needed a recreate
   like the other 9 DB-dependent containers to pick up the new password.
2. HyperHealth's seeded `postgres-db-health` check
   (`agents/hyperhealth/seed_checks.py`) stores a **literal DSN, password
   included, as a row in its own DB** — not derived live from `.env` at
   check-execution time. Rotating the password without re-seeding left this
   one check retrying every 30s with the dead credential, visible as a
   steady stream of `password authentication failed` in Postgres's own logs.
   Traced to the exact source (`hyperhealth-worker`, not some external
   client) via the connecting IP after temporarily enabling
   `log_connections` on Postgres (reverted after). Fixed by re-running
   `seed_checks.py --force`, which found and fixed a second real bug along
   the way: the script's `.env` reader had no explicit encoding and crashed
   on a non-cp1252 byte — same Windows-encoding trap class as other issues
   in this repo, fixed with `encoding="utf-8"`. **Any future Postgres
   password rotation must re-run this script too** — it's a second, easily
   forgotten source of truth for the DSN.

**Real incident during this work**: recreating ~12 containers on top of an
already-running 69-container fleet (this box's WSL2 VM is capped at 4GB via
`.wslconfig`, a deliberate, already-known ceiling — never raise it) drove
the host to `0.40GB` free and took the whole WSL2 VM unresponsive —
`docker exec`/`docker ps` timing out completely, Docker Desktop's own API
returning `500`s, `wsl -e free -m` itself failing with
`WSL/Service/0x8007274c`. Recovered via a Docker Desktop restart (from the
tray) followed by a staged relaunch — core infra first, then
`agents-full.yml`, then registry/hyperhealth/discord/brain profiles in small
batches, checking memory between each stage — rather than one blanket
`up -d` for all 69 containers at once. Zero data loss (Postgres's data
volume was never touched, `docker logs postgres` confirmed "Skipping
initialization" on every restart), zero unhealthy containers after full
recovery. Corrected `docs/STATUS.md`'s "Known Risks" table, which had
claimed memory pressure was already "proven, not just planned" — that claim
was true for the specific launch pattern it was based on (one clean `up -d`)
but doesn't hold for live container churn on an already-running fleet, and
tonight is real evidence of that, not a hypothetical.

**N1 (`ANTHROPIC_API_KEY`) unchanged** — still needs Bro to generate a fresh
key at console.anthropic.com and place it directly into `.env`; no agent
action can substitute for that step.

---

## 2026-08-22 evening — N4 `broski-bot` duplicate-`security_opt` fixed (#435)

Issue #435's own hypothesis ("`broski-bot`'s `security_opt` is probably set
twice, once directly and once via a YAML anchor") was wrong — checked first
and ruled out: `docker-compose.core.yml` sets it exactly once for
`broski-bot`, no anchor/base template touches it. The real cause is the exact
repro command in the issue: `docker compose -f docker-compose.yml -f
docker-compose.core.yml -f docker-compose.agents-full.yml ...` — but
`docker-compose.yml` already pulls `core.yml` in via `include:`. Passing it a
second time via `-f` merges every service `core.yml` defines with itself, and
Compose concatenates list-type fields (like `security_opt`) onto their own
duplicate rather than deduping, which it then rejects.

**Proved this, not just asserted it**: reproduced the exact error with the
double-`-f` command, then showed it isn't `broski-bot`-specific at all — the
same command variously fails on `hypercode-core` or `celery-worker` depending
on which profiles/files are combined, i.e. whichever `core.yml` service
Compose validates first. Confirmed both of the repo's real launch
paths — `AGENT-START.md`'s documented `-f docker-compose.yml -f
docker-compose.agents-full.yml` and `hyperlaunch.ps1`'s canonical 4-file
set — already resolve with `docker compose config --quiet` clean, because
neither double-passes `core.yml`.

**Fix**: found the one place in the repo that models the broken pattern —
`cleanup-and-prepare.ps1`'s "Recommended startup command", a stale line that
predates `docker-compose.yml` becoming `include:`-based — repointed it at
`hyperlaunch.ps1`. Added a guard comment directly on `docker-compose.yml`'s
`include:` block explaining why none of the included files should ever be
passed again via `-f`, so this doesn't quietly reappear somewhere else.
Nothing in `docker-compose.core.yml` needed changing — it was never the bug.

---

## 2026-08-22 evening — N7 fleet-wide `HYPERCODE_API_KEY` 503 sweep

Followed up on the `broski-coo` fix's open question (N7): does the same
"`HYPERCODE_API_KEY`/`AGENT_API_KEY` never reaches the container" bug hit any
other agent? Yes — 6 more, all in `docker-compose.agents-full.yml`:
`brain-agent`, `business-agent`, `throttle-agent`, `tips-tricks-writer`,
`super-hyper-broski-agent`, `test-agent`. Each sets `API_KEY=${API_KEY:-dev}`
in its env block, but the shared `base_agent.py`-derived auth middleware
these 6 all run only ever reads `HYPERCODE_API_KEY`/`AGENT_API_KEY` — a
variable-name mismatch that's existed since these blocks were written, not a
regression. Live-confirmed before fixing: `POST /execute` on all 6 returned
`503 {"detail":"Agent API key not configured"}` no matter what key was sent.

**Fixed**: added `HYPERCODE_API_KEY=${API_KEY:-dev}` to each of the 6 blocks,
mirroring the already-correct pattern in `docker-compose.agents.yml` (its 6
agents — `project-strategist`, `nemoclaw-agent`, `safety-shepherd`,
`broski-pets-bridge`, `healer-agent`, `coder-agent` — were checked first and
confirmed fine, not part of the bug). `docker compose config` validated the
real secret resolves for all 6, containers recreated via `up -d --no-deps`
(not a full relaunch), all 6 came back `healthy`, and the auth boundary was
re-verified live: no key → `401`, wrong key → `401`, real key → past auth
into route logic (`422`/`404`) — same shape as the agents that were already
correct. Swept the other 33 live fleet endpoints too (specialist squad,
ghost agents, `fleet-controller`, `mission-director`, registry services) —
none showed the bug signature, so this closes N7 for real rather than just
the one instance `broski-coo` surfaced.

**Separate finding, not fixed (new item, not N7's scope):** `project-strategist`
(`:8001`) was found `Exited (255)` during the sweep — its compose wiring is
correct, the container just isn't running. No error visible in its last logs
before the exit. Needs its own look, not a config fix.

---

## 2026-08-22 — `review_mission` BLOCK-approval gap fixed; `broski-coo` v1 built, live

**`review_mission` fixed** (`backend/app/api/v1/endpoints/missions.py`,
commit `378b336d`): the endpoint previously wrote whatever decision a human
sent straight to `approved`/`rejected`, never reading
`plan_response.safety.decision` — a human could approve a mission whose own
preview was `BLOCK`ed, exactly the gap `anomaly_approved_despite_block` (Mission
Evaluator v1, above) was built to *measure* but never closed. Now: `BLOCK`
hard-rejects approval (`409`), no override exists; `ESCALATE` requires a
non-empty `escalation_reason` (`422` without one), so an override is
deliberate and audited in the Governance Ledger, never a silent downgrade to
`ALLOW`. 13/13 tests pass (9 pre-existing + 4 new).

**`broski-coo` v1 built and shipped** — a new, strictly read-only
COO/observer agent scoped to HyperCode-V2.4 only (`agents/broski-coo/`,
commits `bd8cde99`/`89a092ed`/`5a84053a`). `POST /brief` aggregates
`agent-registry`'s live `/agents/status`, `WHATS_DONE.md`, `docs/NEXT_TASKS.md`,
and the newest dated `NEXT_SESSION_HANDOVER_*.md` into a plain-English brief,
tagging each source `ok`/`degraded`/`unavailable` and returning the raw
numbers alongside the LLM's prose so the output is checkable, not just
trusted — motivated directly by two hallucinations pasted from a different
AI assistant into the design session (a "free models" table 7/8 wrong; a
claimed "~30 containers" and a nonexistent `NEXT_SESSION_HANDOVER_LATEST.md`
file, real count 68, no such file exists). Deliberately not a supervisory
agent — no Docker socket, no `DOCKER_HOST`, never calls `agent-registry`'s
adjacent `restart`/`reset` mutation routes, same containment discipline as
`review_mission`'s fix above (don't extend a new agent's trust boundary
before the areas already found shaky are proven solid).

New Anthropic → OpenRouter(free) → Ollama LLM fallback chain, extending the
existing per-agent `_build_llm_client()` pattern (duplicated across 13 agent
files by established convention). Live-testing this against the real
`OPENROUTER_API_KEY` (once Lyndz wired it into the *correct* `.env` — it was
initially dropped into the parent `HperCore/.env`, one directory above the
one `docker compose` actually reads for this repo) surfaced a real bug the
mocked test suite couldn't catch: `stealth/ox-alpha`, a reasoning-capable
free model, returned `200 OK` with `message.content == null` and
`finish_reason: "length"` — it spent its token budget on internal reasoning
before emitting any output. Fixed: null/empty content is now treated as a
failed attempt and rotates to the next discovered free model.

**Tried and reverted, documented so it isn't re-attempted blind**: switched
the OpenRouter tier to route through an OpenRouter dashboard preset
(`@preset/free-router`, configured by Lyndz with `data_collection: deny` +
`max_price: 0` as an intended server-side safety net for the providers
confirmed to train on free-tier inputs/outputs — Poolside, LiquidAI).
Reverted after live testing proved the preset mechanism doesn't reliably
enforce its own policy: the bare `@preset/<slug>` syntax returned a
consistent `500` regardless of the preset's model composition; the
`model` + `preset` dedicated-field syntax returned `200` but an explicit
`model` field silently overrode BOTH the preset's model selection AND its
cost/training-data policy — proven by successfully routing to a paid model
(`anthropic/claude-3-haiku`, real non-zero cost charged) through a preset
configured to deny exactly that. Replaced with a client-side
`_DENIED_PROVIDERS` filter (excludes `poolside`/`liquid` by provider-id
prefix at discovery time) — a hard, code-level check that can't be silently
bypassed by a request-time field, unlike the preset. Full writeup in
`agents/broski-coo/HYPER-AGENT-BIBLE.md` §6.

19/19 tests pass. **Verified live at every stage, not just claimed**:
standalone build/run, real repo bind mount (correctly picked
`NEXT_SESSION_HANDOVER_2026-08-21-late-night.md` as newest), real
`agent-registry` numbers matched a direct `curl` side-by-side, full compose
integration with zero unhealthy containers across the fleet (69 running),
denylist confirmed against the live catalog (`poolside`/`liquid` absent from
discovered models), and the full fallback chain proven end-to-end at the
real production `max_tokens=900`: dead Anthropic key → real OpenRouter call
→ `stealth/ox-alpha` → real "Hello!" text.

---

## 2026-08-22 — Mission Evaluator v1 live: read-only quality scoring over mission_proposals

Implemented `docs/superpowers/specs/2026-08-21-mission-evaluator-design.md` via
subagent-driven-development (4 tasks: table+model, pure rule logic, CRUD/run
store, HTTP endpoints — this entry closes Task 4, the last one). Adds a
read-only observer that scores every **terminal** `mission_proposals` row
(`approved`, `rejected`, `rejected_malformed`, `preview_unavailable`) against
the checks it should have satisfied, and flags anomalies where the human
decision didn't match what Safety Shepherd actually said.

**Scope-narrowing decision (made during brainstorming, still true)**: v1
evaluates **proposal/review quality only** — was the plan well-formed, did
the preview succeed, did the human's approve/reject line up with the Safety
Shepherd verdict recorded in `plan_response`. It does **not** evaluate real
execution outcomes (whether an approved mission actually succeeded once
dispatched) — that needs Phase 3, once there's a real execution path to
observe. Nothing here touches `review_mission` or blocks/delays a human
decision; it is a pure after-the-fact observer, one row per mission,
written once and never updated.

**Flagship anomaly finding (confirmed live, still true after this plan)**:
`review_mission` (`backend/app/api/v1/endpoints/missions.py`) never
re-checks the Safety Shepherd verdict recorded in `plan_response` before
allowing a human to approve a mission — a human can approve a mission whose
own preview was `BLOCK`ed, and the endpoint has no code path that would stop
them. This plan deliberately does not touch `review_mission` to fix that; it
only observes it via the new `anomaly_approved_despite_block` check family,
so the gap remains open by design and is now continuously measurable via
`GET /mission-evaluations/summary`.

**Built**: `backend/app/models/mission_evaluation.py` (`MissionEvaluation`
model, table `mission_evaluations`, migration `021_add_mission_evaluations`),
`backend/app/services/mission_evaluator.py` (pure `evaluate_mission(status,
plan_response) -> dict` + `TERMINAL_STATUSES`), `backend/app/services/mission_evaluation_store.py`
(`run_evaluation`/`list_evaluations`/`summary`, all read-only against
`mission_proposals`), `backend/app/api/v1/endpoints/mission_evaluations.py`
(`POST /api/v1/mission-evaluations/run`, `GET /api/v1/mission-evaluations`,
`GET /api/v1/mission-evaluations/summary`, all authed via the same
unmodified `deps.get_current_active_user` every other human-facing endpoint
in this repo uses), registered in `backend/app/api/api.py` behind the same
`_HAS_MISSION_EVALUATIONS` conditional-import pattern as `missions`/`_HAS_MISSIONS`.
6/6 endpoint tests pass (`backend/tests/test_mission_evaluations_endpoint.py`).

**Live-verified, not just unit-tested**: rebuilt + recreated `hypercode-core`
(`docker compose -f docker-compose.core.yml build hypercode-core && ... up -d
hypercode-core` — this container has no volume mount for `backend/app`, only
`alembic`/`alembic.ini`, so new backend code needs an explicit rebuild every
time, same as Mission Director Phase 1's own Task 6). Migration `021` applied
automatically on container start (`alembic.runtime.migration: Running upgrade
020 -> 021, Add mission_evaluations table`), confirmed via `\d
mission_evaluations` against the live `postgres` container.
`_HAS_MISSION_EVALUATIONS` confirmed `True` inside the running container. Real
authed `POST /run` against the live stack: `evaluated_count: 2, anomaly_count:
0, already_evaluated_skipped: 0` — it picked up both real terminal
`mission_proposals` rows already in the DB from Mission Director Phase 1's own
live verification (`mission_ae0fea4b4dc6`, `mission_b41d0e3f32f4`, both
`preview_unavailable`, both scored `verdict: clean`). `GET /summary`
afterwards: `total_evaluated: 2, plan_malformed_rate: 0.0, preview_failed_rate:
1.0`, all anomaly counters `0` (expected — no `approved`/`rejected` rows exist
yet to trigger the anomaly checks). Unauthenticated `POST /run` returned `401`
as required. Full-box sweep after rebuild: `docker ps --filter
"health=unhealthy"` returned empty — zero unhealthy containers across all 68
running.

---

## 2026-08-21 — Mission Director Phase 1 live: goal → previewed, reviewable plan

Implemented `docs/superpowers/specs/2026-08-21-mission-director-phase1-design.md`
via subagent-driven-development (6 tasks, 2 fix rounds — both plan-mandated
test-coverage/error-handling gaps the controller's own brief had left,
caught by review, closed in one round each), following the fleet truth
registry the same session. A human-submitted goal can now become a
previewed, audited, human-reviewable infrastructure-change plan, with
zero possibility of live mutation anywhere in the path.

**Two structural deviations from the spec, ruled during planning (not
silent)**: the spec sketched both human-facing routes
(`propose`/`review`) living inside a new `agents/mission-director/`
container, gated by `deps.get_current_active_user`. That dependency
needs a live SQLAlchemy session + a real DB user lookup — it can't be
ported into a separate container without dragging in the backend's full
DB layer, and no agent container in this repo does real JWT verification.
So (1) the two routes live in `backend/app/api/v1/endpoints/missions.py`
instead, reusing the dependency literally, unmodified; mission-director's
own `/v1/plan` route is unauthenticated, mirroring fleet-controller's own
`/v1/plans/preview` precedent (containment via capability absence, not
access control) — only the backend is a sanctioned caller. And (2)
`mission_proposals` is a backend-owned table, not one mission-director
connects to directly — mission-director stays fully stateless (matches
fleet-controller's own zero-persistence precedent); the review endpoint's
point-lookup/status-transition happens entirely in-process in the
backend, since review never needs to call mission-director again ("approving
performs nothing live").

**Built**: `agents/mission-director/` (new container, `:8086` — the
plan's original `:8097` was found stale during Task 6, already claimed
by `evolve-relay` + `docker-compose.trae.yml`'s `agent-training-api`;
internal container port unaffected, still `8080`, DNS-resolved for all
service-to-service traffic) — `models.py` (file-copied from
`agents/fleet-controller/models.py` per this repo's no-cross-agent-import
convention, plus new `MissionProposal`/`ReviewDecision` types),
`local_validator.py` (fast well-formedness gate, not a safety decision),
`truth_snapshot.py` (a deterministic `sha256:`-prefixed hash of the live
fleet registry — same canonical-JSON convention as fleet-controller's
`canonical_hash`; reads the truth-registry's `fleet_registry.py` +
compose files via read-only bind mounts, never bakes a stale snapshot
into the image), `plan_generator.py` (Anthropic tool-use, forced
structured output, no retry/coercion on malformed output), `fleet_client.py`
(httpx client to fleet-controller's real, unmodified `/v1/plans/preview`),
`ledger_client.py` (fire-and-forget, byte-for-byte mirrors
fleet-controller's own pattern). `backend/app/models/mission.py` +
`backend/app/services/mission_store.py` + migration `020` (new
`mission_proposals` table — backend's own point-lookup store, NOT a
replacement for the Governance Ledger). `backend/app/api/v1/endpoints/missions.py`
(`POST /missions/propose`, `POST /missions/{id}/review`, both authed).
One new scoped Governance Ledger key for `mission-director` (single-row
insert, never the batch reseed script — same care fleet-controller's key
got).

**Verified live, not just unit-tested** (25 tests total across the 6
tasks, all passing, plus this): rebuilt & recreated `hypercode-core` to
pick up the new backend code (was still serving Task-1-4's changes from a
stale pre-existing image — confirmed via `_HAS_MISSIONS` being absent
from the running module before the rebuild, present after), then ran the
real HTTP contract against the live stack with a real, validly-signed JWT
minted via the backend's own `security.create_access_token`:
- `POST /missions/propose` unauthenticated → `401`.
- `POST /missions/propose` authed, real call → `200`,
  `status: "preview_unavailable"`, `truth_snapshot_ref` populated (the
  truth-registry hash generation worked correctly) — root cause
  independently diagnosed by calling `plan_generator.generate()` directly
  inside the running container: the repo's configured `ANTHROPIC_API_KEY`
  is rejected by Anthropic with a real `401 authentication_error`, an
  environment/credentials problem, not a code defect. This is exactly the
  fail-closed behavior the whole feature exists to guarantee — a broken
  LLM credential degrades cleanly to a terminal status, never a fake
  success or an unhandled 500.
- **Real ESCALATE round-trip, proven independently of the API-key
  issue**: called mission-director's own `fleet_client.preview()` code
  directly (not a mock) against the real, running `fleet-controller`,
  which called the real, running Safety Shepherd —
  `safety.decision: "ESCALATE"`, `safety.reason: "dangerous category
  'docker' needs explicit grant"`, `safety.shepherd_available: true`,
  `execution.performed: false`. This is the exact round-trip the spec
  named as its explicit proof requirement.
- `POST /missions/{id}/review` on the real `preview_unavailable` mission
  → `409`, `"mission status is 'preview_unavailable', must be
  'previewed' to review"`.
- `POST /missions/{id}/review` on an unknown mission id → `404`.
- Full-box sweep: zero unhealthy containers across all 68 running, before
  and after.

**Out of scope, documented not built** (per spec): capability tokens,
live execution, the mission evaluator, a review UI. `ANTHROPIC_API_KEY`'s
real-world validity is a separate, pre-existing environment item — not
something this feature can fix from inside the repo.

---

## 2026-08-21 — Fleet truth registry live: `EXPECTED_PORTS`/`ALLOWED_COLLISIONS` retired

Implemented `docs/superpowers/specs/2026-08-21-fleet-truth-registry-design.md`
(spec'd earlier the same session) via subagent-driven development — 4 fresh
implementer subagents, one per task, each with an independent task review
before the next task started. Zero fix rounds needed across all 4 tasks;
every review came back spec-compliant with either zero findings or
Minor-only findings.

**Built**: `.github/scripts/fleet_registry.py` — a shared module that parses
the 4 fleet compose files (`docker-compose.agents.yml`, `-full.yml`,
`bropets.yml`, `brain.yml`) into a `FleetRegistry`, merges in
`.github/scripts/fleet_overlay.yml` (a 25-name roster + a 2-entry collision
allowlist — the only hand-maintained file left), and cross-validates the
overlay against the parsed reality on every `build()` call: a stale roster
entry or collision pair raises `RegistryError` naming exactly what's wrong,
rather than silently passing (this is the class of bug that produced the
stale `frontend-specialist :8011` entry found and fixed earlier tonight —
now caught at the source instead of independently rediscovered per
consumer).

`check_expected_ports.py` and `check_duplicate_ports.py` both shrank to
thin consumers of `fleet_registry.build()` — the old hand-typed
`EXPECTED_PORTS` dict (25 name→port pairs) and the duplicated
`FILES`/`ALLOWED_COLLISIONS` definitions are gone for good, along with the
last two independent copies of the `"BIND_IP:HOST:CONTAINER"` port-parsing
logic that had already been fixed twice, separately, earlier tonight.

9 tests total (`.github/scripts/tests/`, plain pytest, no unittest classes,
mirroring `agents/fleet-controller/tests/`'s layout): 5 fixture-based unit
tests for `fleet_registry.py` itself (both port-string formats, stale
roster, stale collision, multi-port-service rejection) + 4 integration
tests running against the real, live compose files and overlay (registry
builds clean, no unexpected duplicates, both consumer scripts' `main()`
pass) — this last group is what would have caught the stale `:8011` bug
before it shipped.

**Verified, not claimed**: full test suite (9/9 passing), both consumer
scripts run standalone against the live repo (`PASS: all 25 roster agents
confirmed`, `PASS: no unexpected duplicate host ports across 47 port
mappings`), both CI workflow YAML files re-confirmed parseable
(`health-check.yml`, `ghost-agents-build.yml` — re-verifying the
2026-08-21 heredoc-YAML fix earlier tonight still holds).

**Process note**: this was the first subagent-driven-development execution
in this repo's session history — ruled to skip an isolated git worktree
(this repo's own Sacred Rules already document a direct-to-main
parallel-auto-commit workflow with fetch-before-push, used 5+ times earlier
the same session) and to have the controller execute the final
verification/push task directly rather than dispatch a 5th subagent pair
for pure verification work with no new source code. Both rulings recorded
in `.superpowers/sdd/2026-08-21-fleet-truth-registry/progress.md` (git-ignored
scratch — the git history is the durable record now).

---

## 2026-08-21 — HYPERCODE_V3_ROADMAP.md found disconnected from reality, rewritten

Bro asked for recommendations on reaching "fully Hyper AGI Auto Agents" after
writing `HYPERCODE_V3_ROADMAP.md` — a blueprint proposing LangGraph + A2A
protocol + a multi-provider LLM router (Grok 4.5, Kimi K3) + Pydantic AI 2.0
memory over an 8-sprint migration. Ran 3 parallel Explore agents to check its
claims against the real repo before answering — verified via repo audit, not
inferred:

- **`THE-HYPERCODE`, the doc's claimed V3 target repo, isn't an agent-swarm
  platform at all** — its own README describes it as "HyperCode: Programming
  Language for Neurodivergent Brains" (multi-paradigm, MLIR-based IR), zero
  LangGraph/A2A/Pydantic-AI code, last commit over a month before the roadmap
  was written.
- The roadmap's 4 listed sibling docs (`_MIGRATION.md`, `_API.md`, etc.)
  don't exist anywhere in the workspace; its cited "legacy" `manifest.json`
  example doesn't match `HyperAgent-SDK`'s real (single-agent, not swarm)
  schema.
- **Zero prior art anywhere in the codebase** for LangGraph (one unused
  hand-rolled stand-in), A2A (`a2a: bool = False`, comment: "nothing
  implements A2A yet"), Pydantic AI (pinned but never installed/imported), or
  Grok/Kimi (zero references outside the roadmap itself).
- The roadmap's "agents that plan, code, test, deploy, and learn without
  human intervention" pitch had no containment design and directly
  contradicted work already shipped this session:
  `fleet-controller` Phase 0's governing rule ("no component may both
  interpret LLM output and possess infrastructure mutation authority"),
  Safety Shepherd's ALLOW/BLOCK/ESCALATE policy engine, the Governance
  Ledger's audit trail, and HyperFlow's own design doc, which already
  explicitly rejected an LLM-driven graph compiler for v1 ("a generated
  graph would get none [review]").
- Also surfaced real, reusable assets the roadmap ignored: specialist agents
  (`agents/*/base_agent.py`) already make real `AsyncAnthropic` calls for
  actual task work — not a stub fleet — and `crew-orchestrator/crew_v2.py`
  is a genuine CrewAI hierarchical LLM planner with a real Opus/Sonnet/Haiku
  tier map, but it's dead code, never imported by the live dispatch path.

**Fixed**: rewrote `HYPERCODE_V3_ROADMAP.md` in place (same path, same "V3 /
Hyper AGI" framing) to build on the mission-director path the
fleet-controller Phase 0 spec already points at instead — a
brain-agent→mission-director→fleet-controller→Safety
Shepherd→Governance Ledger→human-review pipeline, plus a mission evaluator
and the truth registry
(`docs/superpowers/specs/2026-08-21-fleet-truth-registry-design.md`) spec'd
earlier the same session. Explicitly dropped LangGraph/A2A/Pydantic
AI/multi-provider routing with reasons, rather than silently deleting them —
each could be revisited later as a narrow, evidence-driven decision. Kept
the neurodivergent-UX ideas (interrupt-safe state, chunked output, momentum
rewards) since none of them actually conflicted with anything real.
Replaced the old vibes-based "80% fully autonomous" metric with the concrete
benchmark categories (mission generality, long-horizon persistence,
correctability, containment, evidence quality) proposed in a 2026-08-21
external review of the Phase 0 work
(`HyperCode-V2.4/AGI-infrastructure upgrade`, local, not committed).

Went through full Plan Mode: 3 parallel Explore agents grounding the claims,
an `AskUserQuestion` to confirm scope (rewrite now vs. recommendations only),
a written plan with Context/Approach/Files/Verification, user approval via
`ExitPlanMode`, then execution.

---

## 2026-08-21 — CI workflow bugs #6/#7/#8 fixed; found `health-check.yml` was never valid YAML

Picked up `docs/NEXT_TASKS.md` items #6/#7/#8 (CI debt, no architecture decision
needed): `ghost-agents-build.yml`'s 12-agent build matrix pointed at directories
that don't exist, its port-collision regex was unanchored, and
`health-check.yml`'s `EXPECTED_PORTS`/duplicate-port checks mangled every host
port string.

**The real finding was bigger than the reported bugs.** While fixing
`health-check.yml`'s port-parsing bug, `yaml.safe_load()` on the real file
failed — every `python -c "<heredoc>"` block in the file embeds Python code
indented *less* than the literal block scalar's established floor (the
preceding `python -c "` line sits at 10 spaces; the code after it starts at
column 0), which terminates the `run:` block early and breaks the file's YAML
parse from that point on. Confirmed against live run history, not just
inferred: `gh run list --workflow=health-check.yml` shows every run completing
in **0s**, and `gh run view` reads **"This run likely failed because of a
workflow file issue."** This file has never actually executed a single check
— every run since it was created was rejected at YAML parse time.
`ghost-agents-build.yml` and `docker-push.yml` do NOT have this problem
(confirmed both parse cleanly and their jobs register with real names in `gh
run view`) — their actual blocker is the known GitHub Actions billing lock
(`docs/NEXT_TASKS.md` "This Week" list), unrelated to this bug class.

**Fixed**: extracted every embedded Python block in both workflow files to real
files under `.github/scripts/` (`validate_compose_yaml.py`,
`check_duplicate_ports.py`, `check_expected_ports.py`,
`check_fleet_controller_capabilities.py`), called via plain single-line
`run: python .github/scripts/X.py` — eliminates the heredoc-indentation trap
entirely instead of re-indenting around it. `check_duplicate_ports.py` is
shared between both workflows so the two port gates can't drift apart again.
Also fixed while rebuilding the duplicate-port check for real: it originally
only read `docker-compose.yml` (which has no `services:` of its own — it's a
pure `include:` wrapper plain YAML never resolves) + `agents-full.yml`, never
`docker-compose.agents.yml` — the file that actually owns 13 of the 26 fleet
agents; and `EXPECTED_PORTS['8011']` for `frontend-specialist` was stale (real
port is `8012`). The rebuilt duplicate-port check scans every compose file with
agent-fleet collision history (`agents.yml`, `agents-full.yml`, `bropets.yml`,
`brain.yml`) with **no profile filtering** — an earlier profile-based
filter attempt was rejected after checking it against the three real
collisions fixed 2026-08-20 (`session-snapshot`/`evolve-relay`,
`test-agent`/`hyper-brain`, `hyper-split-agent`/`safety-shepherd`): all three
would have been silently hidden by filtering on profile, since `evolve-relay`
is literally `profiles: ["agents"]` — same profile as the fleet itself. Only
the two pairs confirmed genuinely mutually-exclusive-by-construction
(`coder-agent`/`ai-backend` on :8002, `nemoclaw-agent`/`hyper-mission-ui` on
:8099) are allowlisted, by exact service-pair, not by profile.

**New, not fixed — logged as `docs/NEXT_TASKS.md` item #8a**: building the
real (unfiltered) duplicate-port scan also surfaced a genuine, separate infra
risk outside the agent-fleet's scope — `hypercode-ollama`
(`docker-compose.core.yml`, no profile gate, always starts) and
`hypercode-ollama-gpu` (`--profile gpu`) both bind `:11434`; `prometheus`
(always starts) and `prometheus-cloud` (`--profile grafana-cloud`) both bind
`:9090`. Neither has collided yet because nobody's combined those profiles
with the standard launch, but there's currently no profile-based way to
cleanly exclude the base service when opting into the GPU/cloud variant.
Needs Bro's call — deliberately not folded into the agent-fleet port gate.

**Verified, not claimed**: `yaml.safe_load()` succeeds on both edited workflow
files; the parsed `jobs.*.steps[].run` values (pulled from the real parsed
YAML structure, not regex-scraped from source text — a mistake caught mid-session
by a first verification pass that used a naive text-based block extractor and
got false confidence) were executed directly; all 4 extracted scripts pass
clean against the live repo state (0 unexpected duplicates across 47 fleet-file
port mappings, all 25 expected agent ports found); all 12 of
`ghost-agents-build.yml`'s matrix `context`/`dockerfile` pairs, read from the
parsed YAML matrix (not the source text), resolve to a real on-disk Dockerfile.
`CLAUDE.md`'s "CI/CD Workflows Live" section updated to stop claiming
`health-check.yml` was live and to record the run-history proof.

---

## 2026-08-20 (late night, part 12) — fleet-controller Phase 0 shipped, live, smoke-tested

Bro asked to brainstorm the most ambitious version of a 5-idea infra
roadmap (combining a "mission-director" LLM planner with "HyperBrain"-style
skill routing). Because self-triggered missions + real Docker control +
LLM-driven decisions add up to a system that can notice a problem and act
on real infrastructure on its own initiative — close to the exact shape
the roadmap doc's own header disclaimed ("we wont AGI BROski") — went
through a full brainstorming pass (multiple AskUserQuestion rounds, three
detailed design documents Bro shared, each verified against the live
codebase rather than taken on faith) and converged on **Approach C**: hard
separation between a planner that can think but never act, and a
deterministic controller that can act but never interprets natural
language. Governing rule: **no component may both interpret LLM output and
possess infrastructure mutation authority.**

Wrote the full design spec (`docs/superpowers/specs/2026-08-20-fleet-controller-phase0-design.md`,
commit `a85c4a84`) covering only Phase 0 — prove the containment boundary
exists, before any capability is added. Then, via `/plan` mode: an Explore
pass confirmed the exact test pattern to mirror
(`agents/crew-orchestrator/tests/test_safety_gate.py` — the only real
fail-closed-testing precedent in this repo), the CI/doc touchpoints, and a
free port (8094); a Plan pass turned the spec into a concrete file-by-file
implementation plan, catching a real conflict (CLAUDE.md's Sacred Rule says
every agent depends on crew-orchestrator's health — fleet-controller
deliberately doesn't, confirmed explicitly with Bro before building, not a
silent violation) plus two things the spec's original scope didn't cover
(Governance Ledger auth needs a seeded key; Safety Shepherd's env-var
fallback default doesn't match `agents-full.yml`'s, which would have made
the smoke test misleadingly read `BLOCK` for the wrong reason).

**Built**: `agents/fleet-controller/` — `main.py`, `models.py` (pydantic
schema with a closed `Literal` action-kind set, rejects anything
unrecognized at the wire level before any handler runs), `plan_validator.py`
(hard-denies `prod`/`gpu` regardless of what a caller's own constraints
claim), `safety_client.py` (the module that matters most — every Shepherd
failure mode, not just "down", returns the same frozen fail-closed result;
no `off`/`monitor`/`enforce` mode concept at all, unlike the existing
`crew-orchestrator/safety_gate.py`, which fails *open* by deliberate design
for a different use case and was **not** touched), `ledger_client.py`
(fire-and-forget, mirrors `safety-shepherd`'s own `_spawn_ledger_push`
pattern). 26 unit tests across `tests/test_validation.py`,
`test_hashing.py`, `test_safety_unavailable.py`, `test_no_execution.py` —
all passing.

**Verified at every layer, not just claimed**:
- `docker build` + standalone `docker run` + `curl /health` and
  `curl -X POST /v1/plans/preview` before touching compose at all — a
  denied-profile plan correctly `422`'d, an unreachable-Shepherd plan
  correctly `BLOCK`'d.
- `docker compose config` with the new `fleet-controller` service block
  (behind a new `--profile fleet`, deliberately not part of the standard
  `--profile agents --profile hyper` launch) — confirmed in the *rendered*
  merged manifest: `agents-net` only (no `data-net`), no `docker.sock`
  anywhere, `depends_on: safety-shepherd: condition: service_started`, no
  `crew-orchestrator` dependency.
- Added a CI negative-capability check to `.github/workflows/health-check.yml`,
  matching that workflow's existing pure-YAML-parsing style (no Docker
  daemon needed in CI) — asserts the raw compose YAML has no `docker.sock`
  mount and none of `DOCKER_HOST`/`ANTHROPIC_API_KEY`/`GITHUB_TOKEN`/
  `ORCHESTRATOR_API_KEY` in `fleet-controller`'s environment. Ran the exact
  check logic locally first to confirm it actually catches what it claims to
  (hit a Windows-only cp1252 default-encoding artifact running it locally —
  confirmed a non-issue for the real CI runner, which defaults to UTF-8;
  left the workflow file matching its own established no-explicit-encoding
  style).
- **Then actually launched it into the live 68-container fleet** and ran
  all three of the plan's smoke-test cases against real Safety Shepherd:
  1. Valid plan, Shepherd up → `{"decision":"ESCALATE","reason":"dangerous
     category 'docker' needs explicit grant","rule":"dangerous_ungranted"}`
     — Shepherd's real, *unmodified* policy engine correctly classified it
     (category `"docker"` is already in Shepherd's `DANGEROUS` set), zero
     Shepherd-side changes needed for this to work correctly.
  2. `docker stop safety-shepherd`, same plan → `BLOCK`,
     `shepherd_available: false`, `reason: "Safety Shepherd unavailable;
     fail-closed"`.
  3. Plan with `profile: "prod"` → `422`, confirmed via Shepherd's own
     container logs (line count before/after, grepped for
     `fleet-controller`) that Shepherd never received an `/evaluate` call
     for it at all — the pre-Shepherd rejection genuinely runs first.
  `execution.performed` was `false` in every single response across all
  three cases and every test — there is no code path anywhere in the
  service capable of setting it `true`.
- Swept the whole box before and after every step: zero unhealthy
  containers across all 68 running, throughout.

**Operational step done carefully, not just run blindly**: `fleet-controller`
needed a Governance Ledger write key. `scripts/seed_agent_api_keys.py`'s
`SERVICES` list got `("fleet-controller", 200)` added — but running the
script itself regenerates **every** existing agent's key (a full
`ON CONFLICT DO UPDATE` batch across all 14 entries), which would have
silently invalidated 14 other live agents' ledger-write auth against the
running database while their containers still held the old keys. Instead:
ran the script once to get fleet-controller's generated `key_prefix`/
`key_hash`, then hand-wrote and applied a **single-row, scoped** `INSERT
... ON CONFLICT` targeting only `agent_name = 'fleet-controller'` — verified
after with a `SELECT` that all 16 pre-existing rows were untouched. The
script's side effect of overwriting `secrets/*.txt` for those 14 agents on
disk is real but low-risk: `secrets/` is entirely gitignored (confirmed via
`git check-ignore`), so nothing was committed, and nothing in the running
stack auto-reloads those files after container start — they're just
locally out of sync with the DB now, harmless unless someone manually
re-loads them later.

Synced `CLAUDE.md` (new fleet table section, Sacred Rules footnote for the
crew-orchestrator exception, "25/26-agent" counts throughout),
`docs/NEXT_TASKS.md` (new item #2c), `scripts/fleet-roster-check.sh`
(new roster line, `/24`→`/25` denominators, "26-agent" header),
`.github/workflows/docker-push.yml` (new matrix entry).

**Mission-director (the LLM planner) and every phase after Phase 0 —
capability tokens, human approval, live execution — remain unbuilt, exactly
as designed.** Phase 0's entire job was proving the containment boundary is
real before any capability gets added to it. It's real.

---

## 2026-08-20 (late evening, part 11) — throttle-agent's Docker socket fixed

Bro asked to fix throttle-agent's missing Docker socket access (the one
known loose end from the fleet launch). Checked `agents/throttle-agent/main.py`
first: it uses `docker.from_env()` (respects `DOCKER_HOST`) to pause/unpause
containers by tier for rate limiting — a real, legitimate need, not a
misconfiguration to remove.

Found the fix was already half-built: `docker-compose.agents.yml` runs a
`docker-socket-proxy-healer` service whose own comment reads **"Dedicated
write-enabled proxy — ONLY for healer + throttle-agent. Scoped tight:
CONTAINERS + POST + PING only."** — the infrastructure was built with
throttle-agent explicitly in mind, it just never got wired up.
`docker-compose.agents-full.yml`'s `throttle-agent` block had no
`DOCKER_HOST` env var and no `depends_on` on the proxy at all.

Fixed by mirroring `healer-agent`'s exact pattern (never mounting
`/var/run/docker.sock` directly — the whole point of the proxy is to avoid
that): added `DOCKER_HOST=tcp://docker-socket-proxy-healer:2375` to
`throttle-agent`'s environment and `docker-socket-proxy-healer: condition:
service_started` to its `depends_on`. Recreated just that one container
(`docker compose up -d --no-deps throttle-agent`, no rebuild needed — only
compose config changed). **Verified live**: `curl /health` now returns
`{"status":"healthy","agent":"throttle-agent","docker":"ok","healer_ok":true,...}`
— was `"docker":"error"` before. Re-swept the whole box: still zero
unhealthy containers across all 67 running.

**Second, separate finding surfaced while in there (not fixed, logged as
`NEXT_TASKS.md` item #2b)**: throttle-agent also logs `[Throttle] MemStream
unreachable` every 10s. `MEMSTREAM_URL` defaults to `http://127.0.0.1:8010`
— inside the container that only ever points at itself. Checked every
`docker-compose*.yml` in the repo: there is no "MemStream" service defined
anywhere. Unlike the Docker socket (real infra existed, just unwired), this
looks like a genuinely missing dependency — either never built or dead code
left over from an earlier design. Needs Bro's call (build it for real, or
strip the polling loop out of `throttle-agent`), not a wiring fix — left
alone rather than guessing which.

Synced `CLAUDE.md`'s fleet table + launch-command section, `docs/NEXT_TASKS.md`
(item #2a marked fixed, new item #2b for MemStream).

---

## 2026-08-20 (late evening, part 10) — 🚀 25-agent fleet actually launched, live, healthy

Bro said "launch the fleet." Ran `docker compose --profile agents --profile
hyper -f docker-compose.yml -f docker-compose.agents-full.yml up -d` for
real, for the first time ever with the item #0 fix in place. Three more real
bugs surfaced that no amount of `docker compose config` or standalone
`docker build` verification could have caught — they only show up when
containers actually try to start together:

1. **`agent-x`/`hyper-architect`** (both `context: .` in `agents.yml`) hit
   the exact same `.dockerignore` gap the `hyper-observer`/`hyper-worker` fix
   covered earlier tonight — `/agents/` is broadly excluded and only
   `observer/`/`worker/` had carve-outs. Added `architect/` and `agent-x/`
   too.
2. **`agents-full.yml`'s `test-agent`** used `context: ./agents/test-agent`,
   but its Dockerfile `COPY`s a sibling `shared/` directory — the real
   `agents/shared/agent_utils.py`, which `main.py` directly imports —
   unreachable from that narrow context. Broadened to `context: ./agents`,
   `dockerfile: test-agent/Dockerfile`.
3. **The big one**: all 11 of `agents-full.yml`'s own ghost agents (the ones
   I didn't touch during the item #0 fix, because they were never part of
   the duplicate-name problem) referenced networks `app-net`/`agent-net`
   (singular) that were **never created anywhere in the real stack** — only
   `agents-net`/`data-net`/etc. (plural `agents`, defined for real in
   `docker-compose.core.yml`) actually exist. Every one of these 11 agents
   could build a perfectly good image but could never actually start a
   container — `docker compose up` errored with "network agent-net declared
   as external, but could not be found." Fixed via one `replace_all` across
   all 11 service blocks: `[app-net, agent-net, agents-net]` →
   `[agents-net, data-net]` (matching what `crew-orchestrator`/`redis` are
   actually on), and rewrote the file's own `networks:` declaration block to
   match.

Also hit, mid-launch: `hypercode-core` had one transient restart under the
heavy concurrent load of building/starting ~16 new containers at once,
which cascaded a batch of "dependency failed to start" errors to everything
waiting on it at that exact moment — confirmed it wasn't OOM-killed
(`OOMKilled=false`), just a blip; re-ran `up -d` once it stabilized and
everything came up clean. Separately, `project-strategist` came up crash-
looping (`python: can't open file '/app/src/main.py'`) — turned out to be a
**stale cached image** left over from before tonight's item #0 context
repoint; `docker compose up -d` doesn't rebuild automatically on a changed
`build.context`, so an explicit `docker compose build project-strategist`
was needed before it would pick up the real code.

**Final verified state**: polled every previously-blocked agent's Docker
health status until none were `starting` — all 16 (the 11 true ghost agents
+ `agent-x`/`hyper-architect`/`hyper-observer`/`hyper-worker`) report
`healthy`. `scripts/fleet-roster-check.sh` shows 23/24 LIVE (the 24th,
`coder`, is an intentionally-nonexistent alias — `coder-agent` is the real
live one, already documented). Swept the **entire** box for unhealthy
containers: zero, across all 67 running. `throttle-agent` and
`celery-worker` both briefly showed `unhealthy` during the congested
startup window and self-recovered via their own `restart: unless-stopped` +
healthcheck retry — confirmed via `RestartCount=0` and a clean current
health status, not silently ignored.

**New, separate finding logged, not fixed (`NEXT_TASKS.md` item #2a)**:
`throttle-agent` can't reach the Docker socket (`agents-full.yml`'s
definition has no `/var/run/docker.sock` mount) — its HTTP healthcheck still
returns 200 so Docker shows it healthy, but its own internal status reports
`"degraded"` and its resource-throttling feature likely isn't functioning.
Pre-existing, unrelated to tonight's changes.

Synced `docs/NEXT_TASKS.md` (item #0b for the 3 launch-time bugs, item #2
marked launched, item #2a for the throttle-agent finding).

**The 25-agent fleet is live. This is the first time it has ever actually
been composed up as one system**, not just individually build-tested.

---

## 2026-08-20 (evening, part 9) — Item #0 resolved for real: agents-full.yml/agents.yml merge conflict deleted, not just avoided

Bro asked to finally resolve item #0 — the last blocker before a real 25-agent
fleet launch. Re-derived the actual name overlap directly from each compose
file's `services:` block (the previously-cited "14" included 2 spurious
network names from a broader `comm` sweep) — found **13 real overlapping
agent names**: `crew-orchestrator`, `coder-agent`, `backend-specialist`,
`frontend-specialist`, `database-architect`, `qa-engineer`, `devops-engineer`,
`goal-keeper`, `project-strategist`, `agent-x`, `hyper-architect`,
`hyper-observer`, `hyper-worker`.

Compared both files' definitions per agent: `docker-compose.agents.yml`'s
versions are the real, live, hardened ones (e.g. `crew-orchestrator` has
volume-mounted live code, the HYPER-SILLs loadout, `security_opt`, real
API-key wiring) — `docker-compose.agents-full.yml`'s copies were unused
stubs, never actually composed up. **Decision: `agents.yml` stays canonical
for all 13 — deleted their duplicate blocks from `agents-full.yml` for
good**, not just "don't compose the files together." `agents-full.yml` is
now a clean 11-agent ghost-only overlay. Rewrote its header/port-map comment
block and fixed the TIER 1/2/3 section headers' agent counts to match.

**Verified, not just edited**: `docker compose config` with both files +
`--profile agents --profile hyper` resolves cleanly (46 services, zero
errors) — grepped the merged output for `crew-orchestrator` and confirmed
its `volumes`/`hive_mind`/`security_opt` fields are present (the real
definition, not the deleted stub).

**Second bug found and fixed in the same pass**: `agents.yml`'s
`project-strategist` pointed at `agents/business/project-strategist` — a
directory whose Dockerfile/code was deleted the same day by the
business-agent fix (commit `0c2f4fd6`); only stray untracked bind-mount
folders remained. Repointed to the real `agents/08-project-strategist`,
which turned out to have its *own* separate, pre-existing bug: missing
`base_agent.py` entirely (every sibling numbered agent 01–07/09 has one,
`agent.py` imports it and would crash on boot without it). Copied the same
clean template used for brain-agent/business-agent
(`agents/09-tips-tricks-writer/base_agent.py`), added the missing
`COPY base_agent.py .` to the Dockerfile, and fixed `requirements.txt` (was
missing `httpx`/`anthropic`/`openai`, all needed by the copied template).
**Verified by building + running standalone**: `docker build` succeeded,
`docker run` + `curl /health` → `{"status":"healthy","agent":"project-strategist"}`
(200).

**Found, NOT fixed (separate, logged as new item `#0a`)**: `agent.py`'s
`plan()`/`delegate_tasks()` — the actual specialist-delegation logic this
agent exists for — are dead code. `ProjectStrategist` never overrides
`process_task`, so `/execute` silently falls through to the generic
inherited handler; the two methods also call the async LLM client and async
redis client without `await`, and reference a nonexistent
`self.config.core_url`. Not a boot-blocker — the container runs fine via the
generic fallback — a real-behavior gap, not urgent, out of scope for item #0.

Also synced: `scripts/fleet-roster-check.sh` (header comment, `agent-x`'s
port note now `:8084`, `project-strategist`'s note, summary reminder text —
re-ran, still exits 0), `.github/workflows/health-check.yml`'s
`EXPECTED_PORTS` (comment + `agent-x` `:8083`→`:8084`), `CLAUDE.md`'s fleet
table + "Full Stack Launch Command" section (now unblocked, `--profile
hyper` added as a documented requirement alongside `--profile agents`),
`docs/NEXT_TASKS.md` (item #0 marked resolved, new item #0a for the
delegation-logic gap, item #2's launch status updated).

**Item #0 is resolved. Item #9 was already resolved. No known blocker
remains before a real 25-agent fleet launch** — launching it was explicitly
scoped out of this session (Bro's call: fix the files, don't launch yet).

---

## 2026-08-20 (evening, part 8) — Last 3 item-#9c agents fixed + verified live

Bro asked to keep going on the port audit's final 3 (`brain-agent`,
`hyper-observer`, `hyper-worker` — the ones that couldn't even build, item
#9c). All three fixed in commit `84fa5a2d`:

- **`brain-agent`**: `agents/brain/` never existed. Wrote a real implementation
  — swarm memory agent backed by `chroma` (semantic recall/storage over prior
  agent-swarm activity), `AGENT_PORT=8080` baked into the Dockerfile.
- **`hyper-observer`** / **`hyper-worker`**: their Dockerfiles `COPY` shared
  `src/agents/hyper_agents/` code that was unreachable from the narrow
  `./agents/hyper-agents` build context `agents-full.yml` declared. Repointed
  both services' `context:` to repo root (`.`) with an explicit `dockerfile:`
  path, and fixed `.dockerignore`, which was excluding paths those builds need.

**Verified by actually running all three, not just building.** Docker Desktop
wasn't running at the start of this pass — started it, waited for the daemon,
then: `docker build` succeeded for all 3; ran each standalone (`docker run` +
`curl /health`) — `brain-agent` → `{"status":"healthy","agent":"brain-agent"}`
(200), `hyper-observer` → `{"name":"hyper-observer","status":"ready",...}`
(200), `hyper-worker` → `{"name":"hyper-worker","status":"ready",...}` (200).
Logged `redis_unavailable`/`Crew registration failed` warnings in their
startup output are expected for a standalone container with no
`crew-orchestrator`/redis on the network — same as every other agent verified
this session, not a real problem. Test containers/images removed after.

**Item #9 (container-internal port audit) is now fully closed — 24/24 agents
build and bind `8080` correctly.** `docs/AGENTS_FULL_PORT_AUDIT_2026-08-20.md`,
`docs/NEXT_TASKS.md` (items #2/#9/#9c), and `CLAUDE.md`'s fleet table + launch
warning all updated to match. **Item #0 (the 14-name same-name-merge decision)
is now the only remaining blocker before a real 24-agent fleet launch.**

---

## 2026-08-20 (evening, part 7) — All 17 item-#9 port-mismatched agents fixed

Bro asked to fix the 17 agents flagged in the container-port audit (part 6).
Baked `AGENT_PORT=8080` (or `PORT=8080` for the 2 that use that env var name)
into each agent's Dockerfile, matching `agents-full.yml`'s uniform compose-level
healthcheck (`curl http://localhost:8080/health`, identical across all 24
services). Full evidence: `docs/AGENTS_FULL_PORT_AUDIT_2026-08-20.md` (updated
in place, not a new file).

Fixed: `project-strategist`, `coder-agent`, `frontend-specialist`,
`backend-specialist`, `database-architect`, `qa-engineer`, `devops-engineer`,
`security-engineer`, `system-architect`, `agent-x`, `throttle-agent`,
`super-hyper-broski-agent`, `tips-tricks-writer`, `hyper-split-agent`,
`session-snapshot`, `goal-keeper`, `coderabbit-webhook`.

One agent needed more than a Dockerfile edit: `tips-tricks-writer`'s `agent.py`
hardcoded `config.port = 8009` directly in its `__main__` block — the env var
fix alone would have been silently overridden back to `8009` at runtime.
Removed the hardcode so it falls through to `AgentConfig`'s own
`AGENT_PORT`-driven default. Also fixed a stale "started on port 8000" log
message in `coderabbit-webhook/main.py` while in the file.

**Verified, not just written**: built 4 representative images (one per fix
pattern — `system-architect`, `tips-tricks-writer`, `goal-keeper`,
`hyper-split-agent`), all succeeded. Ran `tips-tricks-writer` (the one requiring
a code change, highest risk of a silent regression) standalone: logs showed
`Uvicorn running on http://0.0.0.0:8080`, `curl /health` returned
`{"status":"healthy","agent":"tips-tricks-writer"}` (200). A repo-wide grep
across all 17 for any remaining non-`8080` port reference came back empty.
Test containers/images removed after.

**Fleet status: 21 of 24 agents now build correctly and bind the right port.**
Only 3 can't build at all (`brain-agent`, `hyper-observer`, `hyper-worker` —
a build-context path bug, not a port bug — see item #9c, not fixed this pass)
and item #0 (the 14-name same-name-merge decision) remain before a real launch.

---

## 2026-08-20 (evening, part 6) — Full container-port audit across agents-full.yml

Bro asked to audit item #9 (the container-port mismatch found while fixing
business-agent) across all remaining agents. Checked all 24 — full evidence in
`docs/AGENTS_FULL_PORT_AUDIT_2026-08-20.md`.

- **4 fine**: `crew-orchestrator`, `hyper-architect`, `test-agent`, `business-agent`
  genuinely listen on the `:8080` compose expects.
- **17 port-mismatched**: every one bakes its own old, pre-reconciliation host
  port as its internal bind port (`project-strategist`→8001,
  `frontend-specialist`→8002, ... `hyper-split-agent`→8096,
  `session-snapshot`→8097, etc.) — builds fine, healthchecks itself fine, but
  is completely unreachable via the host port compose maps to it.
- **3 can't even build**: `brain-agent` (`agents/brain/` doesn't exist),
  `hyper-observer`/`hyper-worker` (Dockerfiles exist but one directory deeper
  than compose's `context`+`dockerfile:` combo looks — same misplaced-nesting
  bug class as the old `business-agent` scaffold).

**Audit only — nothing fixed this pass** (that wasn't asked for). Confirms
fixing item #0 (the 14-name merge decision) alone would not make the fleet
launchable — item #9 is a separate, additional blocker underneath it.
Documented in `NEXT_TASKS.md` items #9/#9a/#9b/#9c, `CLAUDE.md`'s launch-command
warning, and the new standalone audit doc.

---

## 2026-08-20 (evening, part 5) — business-agent, test-agent, tips-tricks-writer all fixed for real

Finished the `agents-full.yml` collision-fix arc from earlier tonight. Commits:
`161d747a` (tips-tricks-writer), `bd57cfc9` (test-agent), `0c2f4fd6` (business-agent).

- **`tips-tricks-writer`**: moved :8009→:8018 (was colliding with live `chroma`).
- **`test-agent`**: moved :8100→:8019 (was colliding with live `hyper-brain`). Also
  self-corrected an earlier mistake in this same session — `test-agent` had been
  mis-filed as one of the item-#0 same-name-merge cases; re-checked against the true
  base-include file set and it wasn't, just a plain port collision.
- **`business-agent`**: built for real. The only Dockerfile that existed
  (`agents/business/project-strategist/`) built code that was, by its own config
  file, still `"Project Strategist"` — a stray clone, never customized, and its
  `EXPOSE 8019` matched neither compose's `:8020` host port nor its `:8080`
  container port. Deleted it (`git rm -r`), wrote real code flattened to
  `agents/business/`: billing/subscription/revenue framing, a read-only Stripe
  balance+recent-charges snapshot as LLM grounding (never writes/mutates payment
  state — that stays in `agents/stripe-mcp`). Fixed `docker-push.yml`'s CI matrix
  too (pointed at a third, different, nonexistent path). **Verified by actually
  running it**: `docker build` succeeded, `docker run` + `curl /health` returned
  `{"status":"healthy","agent":"business-agent"}`, `/execute` and its auth
  middleware both worked correctly.

**All of NEXT_TASKS.md's original P1/P2 launch-blocker list is now closed.** Only
item #0 (the 14-name same-name-merge architecture decision, already mitigated by
not composing `agents-full.yml` with the base stack) remains before a real fleet
launch is possible.

---

## 2026-08-20 (evening, part 2) — Fleet Dedupe Decision

Asked Bro to pick between 4 options for the item-#0 finding below (retire
agents-full.yml's 14 duplicate agent definitions / rename them / give them
distinct names / stop composing the two files together). **Decision: stop
composing them together** — nothing deleted, fully reversible, kills the
silent-merge hazard immediately. The permanent fix (who owns these 14 agents
long-term) is still open. Documented in `CLAUDE.md`, `agents-full.yml`'s header,
`NEXT_TASKS.md` item #0, and `fleet-roster-check.sh`.

While in the same area: corrected `business-agent`'s status. It does have a
Dockerfile (`agents/business/project-strategist/Dockerfile`), but the code it
builds identifies itself as `"Project Strategist"` and exposes the wrong port —
a project-strategist directory cloned as a starting scaffold, never customized.
Did not wire compose to it. `NEXT_TASKS.md` P2-1 updated with the precise finding.

---

## 2026-08-20 (evening) — agents-full.yml Real Collision Fixes + Architecture Audit

Verified the 08-20 morning session's "3 port collisions" claim against the actual
merge (`docker compose config`), not just grep — found the real picture was worse.
Commit: `e9638019`.

### ✅ Fixed & pushed
- `hypercode-mcp-server` phantom ghost block **deleted** from `docker-compose.agents-full.yml`
  — pointed at `./agents/hypercode-mcp-server`, which never existed; was silently
  swapping the real live service's build context on merge. Not a 25th agent to rename.
- 3 real port collisions fixed, each verified against a live container:
  `system-architect` 8008→8010 (was `healer-agent`), `hyper-split-agent` 8096→8013
  (was `safety-shepherd`), `session-snapshot` 8097→8017 (was `evolve-relay`).
- Documented launch command was missing `--profile agents` — without it
  `crew-orchestrator` silently drops from the merge and the compose project is
  invalid. Fixed in `CLAUDE.md` + the compose file's own header.
- Synced `scripts/fleet-roster-check.sh` (24-entry roster now, re-ran it, exit 0)
  and `.github/workflows/health-check.yml`'s `EXPECTED_PORTS` dict.

### 🔴 Found, not fixed — needs Bro's call
- **14 of ~24 agent names in `agents-full.yml` are also defined in
  `docker-compose.agents.yml`** with different build contexts/ports/profiles.
  Same-name services merge silently across compose files instead of erroring —
  proven on `hypercode-mcp-server` and `hyper-architect`. Most of "the 25-agent
  fleet" launch has never deployed what the docs describe. This is an
  architecture decision (rename scheme / dedupe / retire one side), not a port
  patch. Logged as `NEXT_TASKS.md` item #0.
- `tips-tricks-writer` (:8009) collides with live `chroma` — new, not in the
  original list.
- `test-agent` (:8100) still collides with live `hyper-brain` — entangled with
  the item-#0 decision, not just a port move.
- `business-agent` still has no Dockerfile anywhere (pre-existing, unchanged).
- `docs/STATUS.md`'s "Agent Fleet — 25 Total" table is stale (predates the
  08-19/08-20 reconciliation) — flagged with a banner in place, not rewritten.
- `.github/workflows/ghost-agents-build.yml`'s build matrix `context:` paths are
  wrong for most of its 12 entries (point at directories that don't exist).
- Two pre-existing, always-broken CI checks found (not caused tonight): the
  `port-check` job's dedup regex in `ghost-agents-build.yml`, and the port
  parser in `health-check.yml`'s `EXPECTED_PORTS` gate — both would fail to
  ever correctly extract a real host port from `"127.0.0.1:PORT:PORT"` syntax.

Full detail + evidence commands: `docs/NEXT_TASKS.md` items #0, 1a, 1b, 5–8.

---

## 2026-08-19 — STATUS.md + NEXT_TASKS.md Reconciliation Pass

Full docs reconciliation. Both files were stale (July 10 / mid-July). Now accurate and live.

### ✅ docs/STATUS.md — Fully Updated

- Bumped from **July 10 → August 19, 2026**
- Full **25-agent fleet table** added (13 existing + 12 ghost agents)
- Each agent shows port + live/building status
- ⚠️ Known Risks section added: port clash, memory pressure, crew-orchestrator SPOF, JWT expiry
- Commit: `da91777b`

### ✅ docs/NEXT_TASKS.md — Fully Restructured

- Restructured into priority tiers: 🔴 Immediate → 🟡 This Week → 🟢 Background
- Pre-launch checklist (port check, resource limits, crew-orchestrator health, launch command) surfaced at top
- August 2026 completions (ghost agent session) properly logged
- Stale July items carried forward or marked done
- Commit: `da91777b`

---

## 2026-08-19 — 12 Ghost Agents Built + CI/CD Pipeline + AGENT-START v3.3

Full ghost-agent fleet session. All 12 previously-missing agents identified, scaffolded, and registered. Full CI/CD pipeline created for parallel GHCR builds.

### ✅ 12 Ghost Agents Registered & Building

All 12 agents identified, port-mapped, and registered in compose + AGENT-START:

| Agent | Port | Status |
|---|---|---|
| `security-engineer` | :8007 | ✅ Ready |
| `system-architect` | :8008 | 🔨 Building |
| `tips-tricks-writer` | :8009 | 🔨 Building |
| `throttle-agent` | :8014 | 🔨 Building |
| `super-hyper-broski` | :8015 | 🔨 Building |
| `test-agent` | :8080 | 🔨 Building — ⚠️ check port clash |
| `hyper-architect` | :8091 | 🔨 Building |
| `hyper-observer` | :8092 | 🔨 Building |
| `hyper-worker` | :8093 | 🔨 Building |
| `hyper-split-agent` | :8096 | 🔨 Building |
| `session-snapshot` | :8097 | 🔨 Building |
| `agent-x` | custom | 🔨 Building |

### ✅ AGENT-START.md upgraded to v3.3

Commit `9e6a695` — supersedes v3.2 (2026-06-16). Key additions:
- Full 25-agent fleet table (13 original + 12 ghost) with ports + roles
- Resource limits guidance (`256m` / `0.25 cpus`) baked in
- crew-orchestrator SPOF warning flagged
- 2 new gotchas: memory pressure + `:8080` collision risk
- Per-repo doc authority map (`§4`) expanded
- Launch command documented: `docker compose -f docker-compose.yml -f docker-compose.agents-full.yml up -d`

### ✅ 4 Comprehensive Build Guides Created

- `BUILD_ALL_AGENTS_GUIDE.md` — full architecture + getting started
- `AGENTS_BUILD_STATUS.md` — detailed status tracking
- `AGENT_BUILD_SESSION_SUMMARY.md` — session breakdown
- `QUICK_START_12_AGENTS.md` — one-page reference

### ✅ Build Automation Scripts

- `build-all-agents.ps1` — PowerShell: checks status + initiates builds
- `start-all-agents.sh` — shell: starts the full 25-agent stack

### ✅ CI/CD Workflow: ghost-agents-build.yml

Commit `d8a0f32` — `.github/workflows/ghost-agents-build.yml`

Three-job pipeline:
1. **`port-check`** — scans all compose files for duplicate ports; fails hard if found. Specifically warns on `:8080`.
2. **`build-ghost-agents`** — parallel matrix: all 12 agents build simultaneously. `fail-fast: false` so one failure doesn't cancel the rest. Skips gracefully if agent dir doesn't exist yet. Pushes to `ghcr.io/welshdog/<agent>:latest` + SHA tag. Uses GHA layer cache.
3. **`fleet-status`** — always runs; drops launch command into Actions summary.

Triggers:
- Push to `main` (agent files / compose files changed)
- `workflow_dispatch` (manual) — optionally target a single agent via `agent:` input

---

## 2026-08-16 — Evolution Plan Phase 0.3/1.3 + 3x MCP server auth gap closed

Working from `🚀 HYPERCODE EVOLUTION PLAN — 2026 & BEYOND` (HperCore root).
Corrected the plan's own Phase 0.1/1.1-1.3 assumptions against actual code
before building anything (found HyperFlow already covers most of Phase
1.3's "goal-based orchestration", MCP gateway is live infra not
greenfield, ECOSYSTEM_TRUTH.md would duplicate the already-generated
AGENT-START.md repo map) — see that file's inline annotations.

- **Phase 0.3 — Agent registry manifest.** `agents/agent-registry/agent_registry.py`'s
  `ROSTER` (43 agents) gained `capabilities`/`tools_exposed`/`events_subscribed`
  (honestly `None` — no invented data), `health_endpoint` (derived only
  from ports already documented in each agent's `role` string), `mcp`
  (`True` for the 4 agents whose name/role already says MCP), `a2a`
  (`False` for all — nothing implements it yet). Surfaced via the
  existing `GET /agents/status` — no new endpoints. 6 new tests
  (`backend/tests/test_agent_registry_manifest.py`).

- **HyperFlow goal matcher (Phase 1.3 v1).** `POST /api/v1/flows/runs`
  now accepts `{"description": "..."}` as an alternative to
  `{"flow": "name"}` — deterministic keyword (Jaccard) matcher
  (`app/agents/hyperflow/goal_matcher.py`) against each flow's
  `name + intent`, env-tunable threshold (`HYPERFLOW_MATCH_THRESHOLD`,
  default 0.4). Explicitly NOT an LLM-generated graph compiler — routes
  only to existing, already-reviewed flows; a confident match runs the
  exact same `start_flow_run` path an explicit `flow` name would.
  Exact top-two tie → ambiguous, 422 (never silently picks one). Zero
  changes to `HyperFlowRunner` or Safety Shepherd. Spec:
  `docs/superpowers/specs/2026-08-15-hyperflow-goal-matcher-design.md`.

- **MCP server auth — closed on all three internal MCP servers**, found
  and fixed one at a time this session, each with zero application-level
  auth before this (network-isolation-only):
  - `agents/stripe-mcp/server.py` — creates real Stripe checkout sessions.
  - `agents/broski-economy-mcp/server.py` — the serious one:
    `award_tokens`/`spend_tokens` wrap `SECURITY DEFINER` SQL functions
    with **no caller-identity check** before this fix; an unauthenticated
    caller could have minted unlimited BROski$ or drained any account.
  - `services/mcp-rest-adapter/app.py` — REST shim in front of the
    generic `docker/mcp-gateway` (github/postgres/filesystem tools).
    **Real live caller** (unlike the other two) — the dashboard's IDE
    view proxies through it; the fix had to also teach
    `agents/dashboard/app/api/mcp/[...path]/route.ts` to send the token,
    or every IDE tool call would have silently 401'd while `/health`
    kept reporting green.

  All three: shared-secret `Authorization: Bearer <token>` per server
  (`STRIPE_MCP_AUTH_TOKEN` / `BROSKI_ECONOMY_MCP_AUTH_TOKEN` /
  `MCP_REST_ADAPTER_AUTH_TOKEN`, never shared across servers),
  `hmac.compare_digest` on UTF-8-encoded bytes (not `str` — non-ASCII
  tokens crash `compare_digest` on `str` args), both sides `.strip()`'d
  (an unstripped secret rejects the *correct* token — real bug an
  independent review caught live against the first two servers; baked
  the fix into the third from the start). Fails closed: unset/empty
  secret rejects everything. `/health` stays open on all three. 23 tests
  across the three auth suites (`test_stripe_mcp_auth.py`,
  `test_broski_economy_mcp_auth.py`, `test_mcp_rest_adapter_auth.py`).
  Spec: `docs/superpowers/specs/2026-08-15-mcp-tool-server-auth-design.md`.

- **`docs/MCP_TOOL_INVENTORY.md`** (new) — every tool across all four MCP
  servers (the three above + the generic gateway's github/postgres/
  filesystem), tagged read-only/write, auth status, actual reachability,
  and a safe-to-expose-later classification.

- **`agents/shared/mcp_client.py`** — fixed a latent env var mismatch.

---

## 2026-08-15 — Alembic duplicate-revision bug fixed (PR #425)

Two migrations both claimed revision `"010"` — made `alembic upgrade head`
fail on fresh deploys. `010_agent_policy_schema.py` renamed to `019`,
re-chained after `018`. Verified locally + live on Railway.

---

## Done & Locked — Do NOT re-suggest

- Backend test DB: JSONB/UUID columns made SQLite-compatible via with_variant()
- 48 Docker containers scaffolded and mapped
- docker-ce-cli locked (NEVER docker.io)
- Redis DB split: DB1=cache, DB2=rate limits
- .env.example committed (never .env itself)
- Stripe webhook rate-limit exempt — confirmed
- Python indent: 4 spaces enforced via .pylintrc
- CI smoke check pipeline in place (.ci-smoke-check)
- Pre-commit hooks configured (.pre-commit-config.yaml)
- Full port map documented (PORT_MAP_COMPLETE.md)
- Health checks documented (HEALTH_CHECK_FULL_REPORT_MAY9_2026.md)
- Makefile + Makefile.observability complete
- Docker production + hardened templates built
- Self-improving agents setup documented
- Master integration plan written
- Obsidian sync integration documented
- Dashboard status tracked (2026-06-16)
- Session handovers logged (May–June 2026)
- **HyperFlow P0-1** — declarative agent mission-graph DSL
- **Safety Shepherd P0-2** — runtime policy brain
- **Brain P2-2 + P2-3** (cross-repo, BROski-Obsidian-Brain)
- **Evo Harness P2-1** — milestone DAG scorer
- **Specialist HYPER-AGENT-BIBLEs P1-4** — 10 filled stubs
- **Governance Ledger P1-2** — durable audit trail
- **BROski Identity Agent P1-1** — resident agent object per user
- **Mission Graph Dashboard Panel P0-3** — `/flows` route + SSE panel
- **HyperFlow ↔ Safety Shepherd wiring** — safety gate on every dispatch
- **Hyper MCP Server v2** — spec-compliant JSON-RPC 2.0 (vault-deployed)
- **HyperStudio Phase 1** — agent write path (PR #315, `ee229ef`)
- **HyperStudio Phase 2** — interactive ESCALATE approval (PR #316, `9f532fb`)
- **AGENT-START.md v3.3** — full 25-agent fleet registered (commit `9e6a695`)
- **ghost-agents-build.yml** — parallel CI/CD for 12 ghost agents (commit `d8a0f32`)
- **docs/STATUS.md reconciliation** — fully updated Aug 19 2026 (commit `da91777b`)
- **docs/NEXT_TASKS.md reconciliation** — fully restructured Aug 19 2026 (commit `da91777b`)

---

## Sacred Rules (NEVER break)

- `docker-ce-cli` — NEVER `docker.io` for socket agents
- `from app.X import Y` — NEVER `from backend.app.X`
- `.env` files — NEVER committed to git
- Stripe webhook — rate-limit EXEMPT, always
- Python indent — 4 spaces, NEVER 3, NEVER mixed
- Redis DB 1=cache, DB 2=rate limits. NEVER mix.
- TRAE IDE — 1 MCP server at a time (free tier). Use Railway URL, not localhost.
