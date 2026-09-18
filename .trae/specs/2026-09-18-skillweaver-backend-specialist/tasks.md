# Backend-Specialist → SkillWeaver Boot Registration - Implementation Plan

Every `rule` TR has a pass/fail condition. Every `rubric` TR has a numeric score with 1/3/5 anchors and a threshold ≥ 4.

---

## Task 1: Curate backend-specialist skill inventory + client-side validator (new file: `agents/02-backend-specialist/skills.py`)
- **Status**: `pending`
- **Priority**: high
- **Depends On**: None
- **Description**:
  - Create `agents/02-backend-specialist/skills.py` containing:
    1. `VALID_CATEGORIES: set[str]` = `{"computation","io","orchestration","optimization","safety","communication","learning","testing"}` (mirrors server enum).
    2. Constant `BACKEND_SPECIALIST_SKILLS: list[dict]` with **6** skills total (exceeds the AC-1 minimum of 4), each covering real agent capabilities per `agent.py` / HYPER-AGENT-BIBLE. Suggested mapping:
       - `execute_backend_plan` → category `orchestration` (plans + approvals + execution)
       - `generate_api_endpoint` → category `io` (creates FastAPI routes like hello/user in agent.py)
       - `database_schema_plan` → category `computation` (generates DB schemas / DDL plans)
       - `business_logic_generation` → category `computation` (writes service-layer business logic)
       - `llm_implementation_plan` → category `learning` (uses Anthropic/Ollama LLM chain per base_agent._build_llm_client)
       - `quality_gate_validation` → category `testing` (approval gating + task validation)
       Each skill MUST have real I/O signature dicts.
    3. `validate_skill_entry(skill: dict) -> list[str]` returning list of human-readable error strings (empty = valid). Validates:
       - required keys present and non-empty (`skill_id, name, description, category, inputs, outputs`)
       - `category in VALID_CATEGORIES`
       - `isinstance(inputs, dict) and isinstance(outputs, dict)` and every key+value is `str`
       - `skill_id` matches regex `^[a-z0-9_]{3,64}$`
    4. `curate_skills_for_registration(skills: list[dict], logger) -> tuple[list[dict], list[dict]]` returning `(valid_batch, dropped_invalid)` with per-skill structured logs via the passed logger (so no print calls). Drops invalid, never sends them.
- **Acceptance Criteria Addressed**: AC-1 (curated inventory + category correctness), AC-3 (validator)
- **Test Requirements**:
  - `rule` TR-1.1: All 6 entries in `BACKEND_SPECIALIST_SKILLS` each return `[]` from `validate_skill_entry()`.
  - `rule` TR-1.2: Inject 4 mutated invalid entries (category=`bogus`, skill_id=`""`, inputs=`["list","not","dict"]`, missing `outputs`) → each returns ≥1 error string.
  - `rule` TR-1.3: `curate_skills_for_registration([mixed_valid_and_invalid], logger)` returns a `valid_batch` with only valid entries, and `dropped_invalid` matches the invalid count.
  - `rubric` TR-1.4: Skill realism dimension; scale 1-5; anchors 1=fictional/vacuous skills, 3=partially real but generic, 5=skills tied to actual code paths in agent.py/base_agent.py with specific I/O matching real task signatures; threshold >=4; evidence code comments + file links in test docstrings.
- **Notes**: No SkillWeaver HTTP needed for this task. Tests run fully offline.

---

## Task 2: Implement registration startup hook + retry + SKILLWEAVER_SKIP_REGISTER guard in agent.py
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 1
- **Description**:
  - In `agents/02-backend-specialist/agent.py` add the following import at top (SDK is on the shared mount path `from shared.skillweaver_sdk import SkillWeaverClient, register_agent_skills`):
  - Override `async def initialize(self)` in class `BackendSpecialist`:
    1. Read `SKILLWEAVER_URL = os.getenv("SKILLWEAVER_URL", "http://skillweaver:8051")`; read `SKILLWEAVER_SKIP_REGISTER = os.getenv("SKILLWEAVER_SKIP_REGISTER", "").strip().lower() == "true"`.
    2. If skip is true → `self.logger.info("skillweaver_registration_skipped", reason="env")`; stash `self._skillweaver_state = {"registered_count": 0, "attempted_count": 0, "status": "unattempted", "last_error": None}`; return early.
    3. Otherwise curate skills via `skills.py curate_skills_for_registration(BACKEND_SPECIALIST_SKILLS, self.logger)`.
    4. Build client `sw = SkillWeaverClient(SKILLWEAVER_URL, timeout=10.0)`.
    5. Wrap `register_agent_skills(sw, self.config.name, valid_batch, best_effort=False)` in a retry coroutine with exponential backoff: attempts=4 total, base=2s, max_sleep=8s; retry on `httpx.ConnectError`, `httpx.ReadTimeout`, `httpx.HTTPStatusError` where `429 <= status < 600 and status != 4xx_except_429` (specifically 5xx + 429, not other 4xx).
    6. After retries exhausted successfully: stash counts in `self._skillweaver_state["registered_count"] = len(registered_ids)`, `attempted_count = len(valid_batch)`, `status="ok"`.
    7. On final exception after retries: stash `status="degraded"`, `last_error = exc_type_name`, `attempted_count = len(valid_batch)`, `registered_count = 0`.
    8. Always `await sw.close()` in `finally`.
  - Wrap the whole initialize override in `asyncio.wait_for(..., timeout=45)` so a hanging network cannot stall boot past NFR-1's ~45s ceiling.
  - Add a health route override (or append to base via middleware): Mount an additional handler in `_setup_routes` or add a `@self.app.get("/health")` override after base init that calls the parent health dict and merges in `skillweaver: self._skillweaver_state`. Ensure the base hardcoded `@self.app.get("/health")` in BaseAgent is shadowed correctly or the state is merged — simplest: call `self.app.routes` after super().__init__ and replace the /health route, or add a `lifespan` context if FastAPI version supports it; if not safe: store state and override _setup_routes by redefining a new /health that reads self._skillweaver_state.
- **Acceptance Criteria Addressed**: AC-2 (health status object ok/degraded/unattempted), AC-4 (retry), AC-5 (skip register), AC-8 (fail-safe), AC-9 (hygiene)
- **Test Requirements**:
  - `rule` TR-2.1: With `SKILLWEAVER_SKIP_REGISTER=true`, `initialize()` runs in <100ms and captured httpx calls (via monkeypatching SkillWeaverClient) = 0, and `self._skillweaver_state["status"] == "unattempted"`.
  - `rule` TR-2.2: Mock SkillWeaverClient `register_skill_batch` to throw `httpx.HTTPStatusError(response=503)` once then succeed on second call → captured calls == 2; final state `status == "ok"`; registered_count matches batch.
  - `rule` TR-2.3: Mock to throw 503 all 4 attempts → final state `status == "degraded"`; no uncaught exception escapes `initialize()`; `attempted_count > 0`; `registered_count == 0`.
  - `rule` TR-2.4: `initialize()` with curate dropping 2 invalid → `attempted_count == 4` for a 6-skill inventory with 2 injected-invalid.
  - `rubric` TR-2.5: Retry shape quality; scale 1-5; anchors 1=no retry or sleeps forever, 3=retry but no backoff or wrong conditions, 5=4-attempt exp-backoff with correct retry-on classes (5xx+429) and skips other 4xx; threshold >=4; evidence pytest test that asserts sleep call counts or timing via mocked asyncio.sleep.
  - `rubric` TR-2.6: Logger usage; scale 1-5; anchors 1=print everywhere or no logs, 3=mixed print/logger, 5=all SkillWeaver events via self.logger.info/warning/error (retry attempt N/4, dropped invalid reasons, skipped flag, success N/M, degraded final); threshold >=4; evidence grep `print(` returns 0 newly added (base_agent shutdown print allowed but unchanged).

---

## Task 3: Dockerfile + compose updates + add SKILLWEAVER_URL env var to backend-specialist service
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Task 2 (files referenced by COPY)
- **Description**:
  - In `agents/02-backend-specialist/Dockerfile`: After the existing `COPY agent.py .` / `COPY base_agent.py .` lines, add `COPY skills.py .` (and any new `tests/` dir if we keep tests alongside; if tests live in repo `tests/agents/` then no COPY needed for tests — see Task 4 decision).
  - In `docker-compose.agents.yml` backend-specialist block:
    1. Add env var `SKILLWEAVER_URL=http://skillweaver:8051` (explicit, matches SDK default so the override path is tested).
    2. Optionally, add a **comment-only** line `# Best-effort SkillWeaver registration: no depends_on so agent boots fast even if SkillWeaver is down` above the service (per OQ-1 default proposal: NO depends_on).
    3. Verify `agents-net` membership (already there, no-op) so DNS `skillweaver:8051` resolves.
  - In `docker-compose.core.yml` verify `skillweaver` service hostname is indeed `skillweaver` (it will be since the service key is `skillweaver`).
  - Add a `python -m compileall -q agents/02-backend-specialist` pre-build smoke check step in a local verify script (not into CI) as Task 4's offline syntax check.
- **Acceptance Criteria Addressed**: AC-7 (staging E2E needs correct build)
- **Test Requirements**:
  - `rule` TR-3.1: `docker compose -f docker-compose.agents.yml -f docker-compose.core.yml config --quiet` exits 0 after edits (yaml valid, no interpolation errors).
  - `rule` TR-3.2: `docker compose -f docker-compose.core.yml -f docker-compose.agents.yml build backend-specialist` completes successfully with exit 0.
  - `rule` TR-3.3: `python -m compileall -q agents/02-backend-specialist/` exits 0.

---

## Task 4: Build + run pytest unit + integration suite
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Tasks 1, 2, 3
- **Description**:
  - Create `agents/02-backend-specialist/tests/test_skillweaver_integration.py` (new file, sibling to agent.py). Structure:
    - `conftest` inline or in same file if pytest auto-discovers.
    - Unit tests (no network) cover TR-1.1 through TR-1.4 and TR-2.1 through TR-2.6 using monkeypatch / respx / unittest.mock.AsyncMock for httpx transports.
    - Optional `@pytest.mark.skipif(os.getenv("TEST_SKILLWEAVER_URL") is None, reason="integration requires TEST_SKILLWEAVER_URL")` integration test `test_end_to_end_register_then_deregister` that performs: new client, register 6 skills via `register_agent_skills` with a unique `agent_id=f"backend-specialist-test-{uuid}"`, list skills via `client.list_skills(agent_id=...)`, assert count=6, then `client.deregister_agent(agent_id)` → list count=0. (This is FR-10.)
  - Run the suite twice:
    1. Pure unit offline mode (no TEST_SKILLWEAVER_URL set): expect all 6+ unit tests PASSED, 1 integration SKIPPED.
    2. After skillweaver container is up and healthy: set `TEST_SKILLWEAVER_URL=http://127.0.0.1:8051`, add `-v --asyncio-mode=auto` and re-run; integration should also PASS.
  - Decide test file location: If repo already has pytest working at repo root with `tests/` dir, alternatively place tests at `tests/agents/test_backend_specialist_skillweaver.py` for consistency. Prefer `agents/02-backend-specialist/tests/` so the module imports are colocated and imports of `skills.py` are trivially relative.
- **Acceptance Criteria Addressed**: AC-3, AC-4, AC-5, AC-6
- **Test Requirements**:
  - `rule` TR-4.1: Offline unit run: ≥6 tests PASSED, 0 FAILED.
  - `rule` TR-4.2: Integration run: `test_end_to_end_register_then_deregister` PASSES when TEST_SKILLWEAVER_URL points at a live SkillWeaver instance.
  - `rubric` TR-4.3: Test quality; scale 1-5; anchors 1=no assertions or flaky depends-on-order, 3=asserts counts but not edge cases, 5=parametrized invalid validator entries, mocked retries with call-count assertions, degraded + skip + ok branches all hit; threshold >=4; evidence test file lines and parametrize decorator counts.

---

## Task 5: Staging verification — compose up, curl proof, degraded scenario
- **Status**: `pending`
- **Priority**: high
- **Depends On**: Tasks 1-4
- **Description**:
  - Execute:
    ```
    docker compose -f docker-compose.yml -f docker-compose.core.yml -f docker-compose.agents.yml --profile agents up -d --build redis skillweaver backend-specialist
    ```
  - Wait ~45s, then run:
    1. `curl -sS http://127.0.0.1:8051/health` → healthy.
    2. `curl -sS http://127.0.0.1:8003/health | jq .skillweaver` → should show status=ok, registered_count equal to curated count (6).
    3. `curl -sS "http://127.0.0.1:8051/api/v1/skills/list?agent_id=backend-specialist" | jq '.count, (.skills[] | {skill_id,category})'` → count=6, all agent_id=backend-specialist, categories in 8-set.
    4. `curl -sS http://127.0.0.1:8051/api/v1/stats | jq '.skills_by_agent["backend-specialist"], .total_skills'` → shows non-empty.
  - Degraded scenario proof (AC-2, AC-8):
    1. `docker compose -f docker-compose.core.yml -f docker-compose.agents.yml stop skillweaver`
    2. `docker compose -f docker-compose.core.yml -f docker-compose.agents.yml up -d --force-recreate backend-specialist` (fresh boot with skillweaver down).
    3. Within 30s: `curl -sS -o /dev/null -w "%{http_code}" http://127.0.0.1:8003/health` → 200.
    4. `curl -sS http://127.0.0.1:8003/health | jq .skillweaver.status` → should equal `degraded`.
    5. `docker logs backend-specialist 2>&1 | grep -i skillweaver` → count ≥1 structured WARN/ERROR about registration failure, no uncaught stack traces.
  - Capture all the above outputs as completion evidence (redacted of env var values — never echo keys).
- **Acceptance Criteria Addressed**: AC-1, AC-2, AC-7, AC-8
- **Test Requirements**:
  - `rule` TR-5.1: Happy-path curls 1-4 each return expected shapes with HTTP 200, and count >= 4 backend-specialist skills.
  - `rule` TR-5.2: Degraded-path curl /health returns 200 within 30s of start, status=degraded, logs contain a skillweaver_registration_failed or equivalent structured line.
  - `rubric` TR-5.3: Staging fidelity; scale 1-5; anchors 1=build fails or container unhealthy, 3=health but skill count 0 or 1, 5=all 6 registered, stats populated, degraded scenario clean; threshold >=4; evidence screenshots/transcripts of the terminal runs.

---

## Task 6: Repo hygiene — WHATS_DONE entry + NEXT_SESSION_HANDOVER update + commit prep
- **Status**: `pending`
- **Priority**: medium
- **Depends On**: Tasks 1-5
- **Description**:
  - Prepend a 2026-09-18 #2 entry (or single entry combining, but keep SKILLWEAVER first section intact per existing handover) to `WHATS_DONE.md` for HyperCode-V2.4 documenting: tasks 1-5 completed, 6 skills registered, degraded behavior, test suite results.
  - Append to `docs/NEXT_SESSION_HANDOVER_2026-09-18.md` (or create next-day file if that one is frozen, but it references today's date so append is fine) a new section:
    - ✅ PROOF SHIPPED: backend-specialist → 6 skills registered on boot; degraded scenario verified; unit 6/6 passed; integration passed.
    - FILES TOUCHED THIS SLICE: `agents/02-backend-specialist/skills.py`, `agents/02-backend-specialist/agent.py`, `agents/02-backend-specialist/Dockerfile`, `docker-compose.agents.yml`, `agents/02-backend-specialist/tests/test_skillweaver_integration.py`, `WHATS_DONE.md`, `NEXT_SESSION_HANDOVER_2026-09-18.md`.
    - **NEXT TASK FOR NEXT AGENT**: Wire 3 more agents — frontend-specialist, database-architect, qa-engineer — same pattern (copy skills.py skeleton, override initialize, build, prove).
  - Commit message prefix `feat: backend-specialist boot SkillWeaver registration + validation + retry + degraded health + tests`.
  - Push instructions for Bro (do not execute push unless asked): `cd HyperCode-V2.4 && git fetch && git rebase origin/main && git status && git add <files> && git commit && git push` — NEVER force-push.
- **Acceptance Criteria Addressed**: Completeness of deliverables, session handoff chain.
- **Test Requirements**:
  - `rule` TR-6.1: `WHATS_DONE.md` new section references the 6 skills + test results (verifiable by grep).
  - `rule` TR-6.2: `NEXT_SESSION_HANDOVER_2026-09-18.md` (existing) updated with files-touched + next-task sentence.
