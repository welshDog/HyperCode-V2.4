# Backend-Specialist → SkillWeaver Boot-Time Skill Registration - Product Requirements Document

## Overview
- **Summary**: Wire the `backend-specialist` agent (Python/FastAPI, `agents/02-backend-specialist/`) so that on container startup it authenticates to the live SkillWeaver service (`http://skillweaver:8051` on `agents-net`), validates a curated set of its real capabilities against SkillWeaver's schema, registers them via the batched SDK endpoint with transient-error retry and best-effort safety, and surfaces registration status through agent logs and the existing `/health` endpoint. Provide unit tests (pytest) for skill validation + retry logic, plus an integration test that verifies the end-to-end round-trip against a real SkillWeaver container using an isolated Redis DB.
- **Purpose**: Close the current gap where `0/26` live agents register any real skills with SkillWeaver. SkillWeaver today only contains hand-curled test fixtures; `/api/v1/stats` reports zero fleet coverage. Backend-specialist is the canonical first agent because it's the cleanest, already has the SDK mount + shutdown de-registration hook in base_agent, and is the blueprint for 3 follow-on agents (frontend-specialist, database-architect, qa-engineer) in the next session.
- **Target Users**: Lyndz BROski (@welshDog) — ND-first autonomous infra platform maintainer; downstream consumers of `/api/v1/stats` and the future SkillFinder dashboard UI; next-session agent doing the 3-agent batch rollout.

## Goals
- G1: On boot, backend-specialist registers **≥4 verified, real, production-relevant skills** into SkillWeaver with correct `agent_id=backend-specialist`.
- G2: Registration tolerates transient SkillWeaver/network failures via **exponential-backoff retry** (max ~30s wall-clock) and never prevents the agent FastAPI server from becoming healthy — the agent must still pass `/health` even if SkillWeaver is unreachable.
- G3: Invalid skill entries (wrong enum category, missing required keys, empty skill_id, bad I/O signatures) are **rejected client-side before any HTTP call**; at least one invalid-skill unit test documents the 400 path via validation error.
- G4: A runnable pytest suite exists that, inside a container with Redis + SkillWeaver reachable (or via test double), proves: boot registration succeeds; retry fires on transient 503; invalid skills are filtered before POST.
- G5: End-to-end staging proof: `docker compose up -d --build backend-specialist skillweaver` (plus redis healthy) → `GET :8051/api/v1/stats` returns a non-empty `by_agent["backend-specialist"]` count matching the curated set, and `GET :8003/health` includes a `skillweaver: {registered: N, status: ok|degraded}` field.

## Non-Goals
- NG1: Does NOT register any other agent (frontend-specialist, database-architect, qa-engineer). They are the next session's work; only backend-specialist ships here.
- NG2: Does NOT add the `/api/skills/proxy` route to hypercode-core. That's roadmap item 2.
- NG3: Does NOT hook the dashboard SkillFinder UI. That's roadmap item 3.
- NG4: Does NOT execute composite skills (`discover_and_compose`) or Phase 1b. Only the registration/validation/retry/health leg is in scope.
- NG5: Does NOT change SkillWeaver server code, category enum, or Redis schema. Agent only; server is the source of truth for validation.
- NG6: Does NOT add a new shared volume mount. The existing `./agents/shared:/app/shared:ro` mount carries `skillweaver_sdk.py` already — import from that path exactly.

## Background & Context
Live truth from [NEXT_SESSION_HANDOVER_2026-09-18.md](file:///h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/docs/NEXT_SESSION_HANDOVER_2026-09-18.md) + [AGENT-START.md](file:///h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/AGENT-START.md) + code:

1. **SkillWeaver is live, tested, bug-fixed.** Container `skillweaver` is healthy on `127.0.0.1:8051`, wired to `redis` with `depends_on: service_healthy`, 3 real bugs fixed 2026-09-18, 8/8 pytest green. APIs proven: `/health`, `/api/v1/skills/register`, `/register_batch`, `/list`, `/discover`, `/compose`, `/stats`, `/compositions/history`. Source of truth for category validation is `SkillCategory` enum in [services/skillweaver/skillweaver.py](file:///h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/services/skillweaver/skillweaver.py#L33-L42):
   `computation | io | orchestration | optimization | safety | communication | learning | testing`.
2. **Import + mount pattern is already agreed and wired.** Compose mounts `./agents/shared:/app/shared:ro` for backend-specialist already (see [docker-compose.agents.yml:1579-1582](file:///h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/docker-compose.agents.yml#L1579-L1582)). [agents/shared/skillweaver_sdk.py](file:///h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/agents/shared/skillweaver_sdk.py) already exists with `SkillWeaverClient(base_url="http://skillweaver:8051" default)` + `register_agent_skills(client, agent_id, skills, best_effort=True)`. No need to build a new SDK module.
3. **Base agent lifecycle hooks are ready.** [agents/02-backend-specialist/base_agent.py](file:///h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/agents/02-backend-specialist/base_agent.py#L187-L308) exposes `async def startup()` (called via FastAPI `on_event("startup")` line 301), `async def shutdown()` which **already contains SkillWeaver de-registration best-effort code** lines 192-216, and `GET /health` line 310. Subclasses override `async def initialize()` for custom hooks — this is the clean injection point. `backend-specialist` requirements.txt already has `httpx>=0.27.0`.
4. **Today's gap:** `base_agent` deregisters on shutdown but **never registers on boot**. No agent writes a skill with `agent_id != "test-fixtures"` into SkillWeaver today. `by_agent` stats are zero for the whole fleet.

## Functional Requirements
- **FR-1 Skill inventory + curation**: A constant `BACKEND_SPECIALIST_SKILLS: list[dict]` exists in `agents/02-backend-specialist/agent.py` (or a new sibling `skills.py` imported by `agent.py`) containing ≥4 skills, each with keys `skill_id, name, description, category, inputs, outputs`; optional `timeout_seconds, examples, version` defaulted per SDK. Each `category` MUST be one of the 8 enum values. Skills MUST be capabilities the backend-specialist actually ships or is documented to perform per [agents/02-backend-specialist/agent.py](file:///h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/agents/02-backend-specialist/agent.py) and HYPER-AGENT-BIBLE (API endpoint generation, database query/build, business logic plan generation, LLM-backed implementation plan with approval gating, input/output contracts mirroring real routes/signatures).
- **FR-2 Boot registration hook**: `BackendSpecialist.initialize()` (override) calls `register_agent_skills()` exactly once per boot, wrapped in a retry decorator/function. The SDK client is constructed with `SkillWeaverClient(os.getenv("SKILLWEAVER_URL", "http://skillweaver:8051"))`. `SKILLWEAVER_URL` env var is honored as an override. `best_effort=False` inside retry so failures propagate to the retry layer; after retries exhaust, the overall registration call is caught and swallowed so `/health` can still respond with `degraded`.
- **FR-3 Retry for transient errors**: Registration implements exponential-backoff retry (base=2s, factor=2, max 4 attempts → 2+4+8 ≤ 14s sleep, wall-clock ≤ ~30s including HTTP timeouts) for conditions: `httpx.ConnectError`, `httpx.ReadTimeout`, any 5xx-class HTTP response, 429 response. Retries MUST NOT fire on 4xx except 429 (4xx = invalid payload, retrying is pointless). After last attempt: log structured error `skillweaver_registration_failed attempts=N last_error=...` and degrade gracefully.
- **FR-4 Client-side skill validation before POST**: A `validate_skill_entry(skill_dict) -> list[str]` validator runs against every dict in the inventory before the batch is built. It checks: required keys present and non-empty (`skill_id, name, description, category, inputs, outputs`); `category in {"computation","io","orchestration","optimization","safety","communication","learning","testing"}`; `inputs/outputs` are `dict[str,str]` (no non-string types); `skill_id` matches `^[a-z0-9_]{3,64}$`. Any failing skill is removed from the batch, logged with `skillweaver_skill_invalid skill_id=... reasons=[...]`, and never sent. If all skills are invalid, a warning is logged and no HTTP call is made.
- **FR-5 Health endpoint extension**: Existing `/health` response at [base_agent.py:310-312](file:///h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/agents/02-backend-specialist/base_agent.py#L310-L312) is extended (via override in BackendSpecialist or by storing state in BaseAgent) to include `skillweaver: {registered_count: int, attempted_count: int, status: "ok"|"degraded"|"unattempted", last_error: str|null}`. This is the staging verification surface.
- **FR-6 Environment/feature flag opt-out**: If `SKILLWEAVER_SKIP_REGISTER=true` env var is set, registration is skipped entirely; `/health` reports `status: "unattempted"`. Useful for CI containers that don't mount agents-net.
- **FR-7 Structured logging**: All SkillWeaver lifecycle events (registration start, registration success N/M, retry attempt N/4, retry exhausted, validation drop per skill, shutdown deregister ok/fail, skip due to flag) use `self.logger.info/warning/error` with keyword args matching the existing structlog adapter — never unstructured `print()` except where the base_agent shutdown hook already does (that pattern is preserved as-is).
- **FR-8 Deregister on shutdown preserved**: No changes to base_agent shutdown deregister flow (it already works; we just provide the matching register side so the deregister has IDs to clean up).
- **FR-9 pytest unit tests**: File `agents/02-backend-specialist/tests/test_skillweaver_integration.py` (or equivalent) with ≥6 unit tests covering: (a) valid skill passes validator; (b) invalid category fails validator; (c) missing `skill_id` fails validator; (d) non-dict `inputs` fails validator; (e) retry fires exactly once on single transient 503 then succeeds on second attempt (via mocked httpx transport); (f) after 4 consecutive 503s the function returns gracefully with degraded state, no uncaught exception; (g) SKILLWEAVER_SKIP_REGISTER=true results in zero HTTP calls.
- **FR-10 Integration smoke-test helper**: A standalone script OR a pytest marker `integration` that runs against live SkillWeaver (reachable via env `TEST_SKILLWEAVER_URL`). This test performs: register 4 curated skills → GET `/list?agent_id=backend-specialist` asserts count=4 → GET `/stats` asserts by_agent bucket non-empty → call deregister → GET `/list?agent_id=backend-specialist` asserts count=0.

## Non-Functional Requirements
- **NFR-1 Fail-closed to fail-open for agent availability**: Agent `/health` MUST return HTTP 200 within 5s from container start even when SkillWeaver is unreachable and retries are fully exhausted. Startup hook registration MUST have its own asyncio `wait_for` ceiling of ~45s; if exceeded, abort registration and mark degraded.
- **NFR-2 Idempotency / duplicate registrations**: Re-registering the same skill_id twice MUST be safe (SkillWeaver already returns `replaced_previous_version: true` on dedupe; we rely on this, do NOT add a pre-check GET per skill — pay one RTT per batch only).
- **NFR-3 No secrets, no env-var echoing**: The code MUST NOT log or print the value of `SKILLWEAVER_URL`, any API key, or any env var value (per [AGENT-START.md:222-223](file:///h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/AGENT-START.md#L222-L223) rule about env var exposure in shell output — applies to code too).
- **NFR-4 No new Python package dependencies for backend-specialist**: `requirements.txt` already ships `httpx>=0.27.0` and `pydantic>=2.5.3`. If validation is implemented with plain dict checks (no new deps) that's preferred; pydantic model allowed because it's already a dep.
- **NFR-5 Python style + indent**: 4-space indent, never mixed, per repo rules [AGENT-START.md:249](file:///h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/AGENT-START.md#L249). Python 3.11.
- **NFR-6 Compose healthcheck not modified**: The existing `curl -f /health` check in compose stays. The extended `/health` payload does not break this (curl -f only checks HTTP status, not body).
- **NFR-7 Image rebuild not bloated**: Dockerfile for backend-specialist copies only new sibling files (e.g., `skills.py`, `tests/` if kept inside agent folder) — ADD/COPY patterns after deps install per existing 2-stage builder layout.
- **NFR-8 Docker compose no port collisions**: backend-specialist :8003 and skillweaver :8051 are already assigned, no new host ports.

## Constraints
- **Technical**: Must run on `python:3.11-slim` backend-specialist runtime; SDK import path fixed as `from shared.skillweaver_sdk import ...` (shared volume mount path); SkillWeaver category enum is frozen as the 8 values above — do NOT extend server enum, only pick from it.
- **Business**: Repo is HyperCode-V2.4 canonical production. `git fetch` then commit + push when done, NEVER force-push. One repo only, no cross-repo commits.
- **Dependencies**: Existing deps only. Test deps added to requirements.txt only if they're not already present (pytest + pytest-asyncio already assumed in repo; verify and add only if missing).

## Assumptions
- A1: `agents/shared/skillweaver_sdk.py` stays in sync with `services/skillweaver/sdk.py` — if drift occurs later a separate sync task is created; this spec does NOT implement a two-way sync or copy step. Treat the shared mount path as canonical.
- A2: SkillWeaver container is on `agents-net` DNS as hostname `skillweaver:8051`. Backend-specialist is already on `agents-net` per compose [docker-compose.agents.yml:1586-1588](file:///h:/HYPERFOCUSZONE/HperCore/HyperCode-V2.4/docker-compose.agents.yml#L1586-L1588).
- A3: Redis data volume persistence is acceptable — re-registration on every container restart overwrites via idempotency. No TTL on skill keys in this spec.
- A4: No LLM call is required to generate skill inventories — skills are hand-written constants that match real code.
- A5: `backend-specialist` compose definition in `docker-compose.agents.yml` already has access to SkillWeaver via shared networks; no additional `depends_on: skillweaver` is required for agent health (best-effort means the agent starts without waiting). We MAY add `depends_on: skillweaver: service_healthy` conditionally or document why not, but it's not required for success.

## Acceptance Criteria

### AC-1: ≥4 verified real skills registered in SkillWeaver on boot
- **Type**: `rule`
- **Given**: `redis`, `skillweaver`, and `backend-specialist` containers are started via `docker compose -f docker-compose.yml -f docker-compose.core.yml -f docker-compose.agents.yml --profile agents up -d --build skillweaver backend-specialist` and all three pass their healthchecks
- **When**: `GET http://127.0.0.1:8051/api/v1/stats` is fetched and parsed, then `GET http://127.0.0.1:8051/api/v1/skills/list?agent_id=backend-specialist` is fetched
- **Then**: (a) `total_skills ≥ 4` in stats includes new entries; (b) the `/list` result has `count ≥ 4` and every returned skill has `agent_id == "backend-specialist"`; (c) each skill's `category` is one of the 8 valid enum values; (d) each skill has non-empty `skill_id, name, description, inputs, outputs`
- **Pass Condition**: All four (a,b,c,d) are true from a single real curl after a clean boot.
- **Evidence**: `curl -sS http://127.0.0.1:8051/api/v1/stats | jq .` + `curl -sS "http://127.0.0.1:8051/api/v1/skills/list?agent_id=backend-specialist" | jq '.skills[] | {skill_id,category,agent_id}'` shell output attached in task completion evidence.

### AC-2: Agent health reports SkillWeaver status with count/status fields + never 5xx
- **Type**: `rule`
- **Given**: backend-specialist container is running, SkillWeaver may or may not be reachable
- **When**: `GET http://127.0.0.1:8003/health` is fetched
- **Then**: (a) HTTP status is always 200; (b) JSON body contains a top-level `skillweaver` object; (c) `skillweaver.registered_count` is integer; (d) `skillweaver.status in {"ok", "degraded", "unattempted"}`; (e) when `SKILLWEAVER_SKIP_REGISTER=true` status is `unattempted`.
- **Pass Condition**: (a-e) true in both "SkillWeaver reachable" and "SkillWeaver unreachable" scenarios.
- **Evidence**: Two separate `/health` curls: one with skillweaver up, one with `docker compose stop skillweaver` + wait 30s for degraded detection.

### AC-3: Client-side validator rejects 4 invalid skill shapes before POST
- **Type**: `rule`
- **Given**: The validation function is callable in pytest
- **When**: Four invalid payloads are passed: (1) category="does_not_exist", (2) skill_id="", (3) inputs=[{"task":"str"}] (list instead of dict), (4) missing key `outputs`
- **Then**: Each returns ≥1 error string, is excluded from the registration batch, and when a test-only httpx spy is installed, zero POST requests occur for an all-invalid batch.
- **Pass Condition**: 4/4 invalid cases each produce ≥1 validation error AND captured HTTP call count = 0 for a 100%-invalid batch.
- **Evidence**: `pytest -v` output of the 4 validator unit tests, all PASSED.

### AC-4: Transient-error retry fires on 503/connect-error and succeeds without raising
- **Type**: `rule`
- **Given**: SkillWeaver client has a mocked httpx transport; first 1 call returns HTTP 503, second returns 200 registered
- **When**: Boot registration runs with retry enabled
- **Then**: (a) 2 HTTP POST calls occur; (b) overall function returns without exception; (c) log output contains a line matching "retry attempt 1/4" or equivalent retry numbering; (d) after 4 consecutive 503s the function still returns without raising and reports `degraded` status.
- **Pass Condition**: Both "1 retry then success" and "4 retries exhausted → no exception" tests pass.
- **Evidence**: pytest -v output for both retry unit tests, passed.

### AC-5: SKILLWEAVER_SKIP_REGISTER env var skips registration cleanly
- **Type**: `rule`
- **Given**: env `SKILLWEAVER_SKIP_REGISTER=true`
- **When**: Agent startup runs
- **Then**: Zero outbound HTTP calls to SkillWeaver host, `/health` reports `status: "unattempted"`, no warning/error logs about SkillWeaver failures (only an info-level "skipped" log).
- **Pass Condition**: HTTP call count = 0 and health status = unattempted.
- **Evidence**: pytest output.

### AC-6: Unit suite passes 6/6 tests without network
- **Type**: `rubric`
- **Dimension**: Unit test coverage quality
- **Scale**: 1-5
- **Anchors**: 1 = 0 tests pass, 3 = 4/6 pass with skips, 5 = 6/6 pass, no external network, all tests runnable without Docker (httpx mocks)
- **Pass Threshold**: >= 4
- **Evidence**: `cd agents/02-backend-specialist && python -m pytest tests/ -v` output (or repo-level pytest) showing green suite.

### AC-7: End-to-end staging run produces /stats with backend-specialist bucket
- **Type**: `rubric`
- **Dimension**: E2E staging fidelity
- **Scale**: 1-5
- **Anchors**: 1 = agent fails to boot or /stats shows no agent; 3 = agent boots, /stats shows some entries but validation/health fields missing; 5 = clean `docker compose up --build` run, redis/skillweaver/backend-specialist all healthy, /stats shows 4+ backend-specialist entries matching curated list, /health has all 4 required skillweaver fields with status=ok.
- **Pass Threshold**: >= 4
- **Evidence**: Terminal shell transcript (redacted of env values) of the compose up + curl sequence, or a run of the integration-marked pytest against `TEST_SKILLWEAVER_URL=http://127.0.0.1:8051`.

### AC-8: Fail-safe — agent remains healthy with SkillWeaver down
- **Type**: `rubric`
- **Dimension**: Graceful degradation quality
- **Scale**: 1-5
- **Anchors**: 1 = Agent /health never returns 200 (hangs or 5xx) when SkillWeaver is down; 3 = Agent eventually healthy but startup takes >60s or spams ERROR logs; 5 = Agent healthy within 10s of container start, max 1 WARN-level structured log about degraded SkillWeaver, no uncaught exceptions, degraded state reflected in /health.
- **Pass Threshold**: >= 4
- **Evidence**: `time docker compose up -d backend-specialist` with `skillweaver` stopped, then repeated `/health` until HTTP 200, then `docker logs backend-specialist 2>&1 | grep -i skillweaver` — wall clock + log output attached.

### AC-9: Code hygiene + no new deps
- **Type**: `rubric`
- **Dimension**: Clean integration with repo conventions
- **Scale**: 1-5
- **Anchors**: 1 = New package deps, wrong import path, or prints env values; 3 = Works but uses print() for new logs or wrong SDK path; 5 = Uses existing shared SDK path, no pip packages added (or adds only pytest deps that were missing), uses self.logger for structured logs, follows 4-space Python indent, matches base_agent patterns.
- **Pass Threshold**: >= 4
- **Evidence**: Diff review of changed files + `grep "pip install\|print("` on new code sections.

## Open Questions
- [ ] **OQ-1:** Do we add `depends_on: skillweaver: service_healthy` to backend-specialist in `docker-compose.agents.yml`, or keep best-effort-only with no wait? Default proposal: keep NO depends_on so agent always boots fast; add a one-line comment above the service block noting the best-effort relationship. If Bro prefers a wait, we switch. — **RESOLVED via approval review.**
- [ ] **OQ-2:** Should the curated skill list live directly in `agent.py` as a module constant, or in a new `skills.py` sibling? Default proposal: new `agents/02-backend-specialist/skills.py` with the constants + validator, imported by `agent.py` — keeps `agent.py` diff minimal and test file next to the logic.
- [ ] **OQ-3:** For the "alerting" path on retry exhaustion, is a structured error log sufficient (NFR-7), or do we want a real Discord alert via the existing `shared/discord_alerts.py` module? Default proposal: structured log only in this slice; Discord alerting can be a follow-up once 3+ agents are wired (single code path for fleet registration alerting).
