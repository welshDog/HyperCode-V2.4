# BROski Phase 3 — `hypercode.run_tests` (async backend test-suite runner via celery-worker)

**Date:** 2026-10-01 · **Status:** draft, awaiting review · **Builds on:** Phase 1 (`hypercode.inspect`, PR #537, merged), Phase 2a (`hypercode.recover`, PR #538, merged), Phase 2b (`authorize`, PR #539, merged) — same `operator-tasks` / HyperFlow catalog, same local-tool convention.

**Branch:** `feature/broski-run-tests`, off `main` (all prior phases merged — no stacking needed this time).

## 0. Where this came from

A pasted AI-generated note (`docs/ideas/2026-09-29-mcp-long-running-tasks-notes.md`) proposed a general "MCP long-running tasks" framework and named `hypercode.run_tests` as the first concrete tool to build. The note assumed an architecture (Celery-driven HyperFlow nodes, `hypercode.inspect`/`hypercode.recover` as still-unbuilt ideas) that doesn't match this repo's real state — both of those are already live. The one genuinely new, useful idea in it survives: give BROski an async tool that actually runs the backend test suite and reports pass/fail, reusing the existing `operator-tasks` poll/approve/cancel machinery. This spec designs that tool against the real codebase, not the note's assumptions.

## 1. Goal

BROski can ask HyperCode to run its own backend test suite without blocking on it: `hypercode.run_tests` returns a task handle immediately (same `operator-tasks` contract as every other operator tool), the actual `pytest` run happens in the existing `celery-worker` container (never inside `hypercode-core`'s own event loop), and polling `hypercode_task_get` eventually returns structured pass/fail/skip counts and duration. No production data or container is ever touched — the suite already runs against an isolated SQLite DB (`backend/tests/conftest.py`), not the live Postgres.

Success for this increment = a live proof that a real `suite: "operator"` run goes end-to-end through the real `celery-worker` (no mocks) and returns correct counts, that a concurrent second call while one is in flight is refused instead of queued, and that nothing in `hypercode-core`, `celery-worker`, or the database is left unhealthy or mutated.

## 2. What changed the scope while designing (verified 2026-10-01)

| Finding | Consequence |
|---|---|
| HyperFlow's `tool` nodes are already a plain `await` of an async Python function (`backend/app/broski_operator/tools.py`'s `LOCAL_TOOLS` dict) with no per-node timeout anywhere in `hyperflow_runner.py` — only `inspect_stack`'s own self-imposed 8s-per-section budget. | No runner changes needed. `local.run_tests` can simply run for minutes; it's a new entry in `LOCAL_TOOLS`, not a new node *type*. |
| The real `/api/v1/operator/tasks` + MCP `hypercode_task_get` poll loop already gives "task_id now, result later" for free, at flow-node granularity (`progress_percent` in `backend/app/broski_operator/status.py` counts completed nodes, not intra-node progress). | This tool's flow has exactly one node, so progress will show `0% → 100%`, not the pasted note's "46% complete" mid-run figure. Explicit v1 scope cut, not an oversight — live sub-task progress would need new plumbing between Celery's result backend and the history/progress model. |
| `backend/tests/conftest.py` already points every test at `sqlite:///./test.db` / an in-memory `sqlite://` — never `HYPERCODE_DB_URL` (the live Postgres). | Running the real suite is data-safe by construction. No new isolation needed, no approval gate needed — this is an `inspect`-style (no-approval) tool, not a `recover`-style (approve/seal) one. |
| `docker-compose.core.yml`'s `celery-worker` has real resource limits (`cpus: "1"`, `memory: 1.5G`) already declared, separate from `hypercode-core`'s own footprint, and is already a standing container (not profile-gated). | Dispatching the actual pytest run there means a runaway/OOM test run can only hurt its own container, never `hypercode-core`'s request-serving — confirms celery-worker is the right execution target, not an in-core subprocess. |
| `app/core/celery_app.py` sets **global** `task_soft_time_limit=300` / `task_time_limit=360` for every task on this worker — there is no per-task ceiling to invent; Celery itself kills the task at 6 minutes regardless of any value this spec's own poll loop uses. | The tool's poll loop must simply poll past 360s and treat "`AsyncResult` never reaches a terminal state by ~400s" as a timeout — it does not need, and must not invent, its own shorter enforcement mechanism. |
| `celery_app.py` defines three real queues (`hypercode-high/normal/low`), even monitored by `tools.py`'s existing `_queues_section` (Redis `LLEN`), with a comment telling new callers to use them — but the only real `celery-worker` command (`docker-compose.core.yml`) is started with `-Q main-queue` only, and no other compose file overrides that command. **Pre-existing, unrelated bug**: those three queues are defined and watched but never actually consumed by anything today. | Out of scope to fix here (touching shared Celery routing for other tasks is a separate, unrelated change). This tool routes to `main-queue` — the one actually consumed — not the "preferred" queue the comment names, because the comment describes an aspiration that isn't true yet. Flagging as a follow-up item (§8), not fixing it. |
| No `pytest-json-report` (or similar) dependency exists in `backend/requirements*.txt`. Pytest's own stdout summary line format isn't a documented stable contract across versions. | Adding `pytest-json-report` (one small, well-known plugin) to `backend/requirements.txt` + `requirements-dev.txt` is in scope — it's the only way to get `{passed, failed, skipped, duration_seconds}` without regex-scraping stdout. |
| The codebase's existing single-use/lock convention is `await redis.set(key, value, nx=True, ex=ttl)` (`agents/governor/redis_state.py`'s replay guard; `backend/app/api/v1/endpoints/hypersync.py`'s idempotency keys) — no dedicated lock helper library. | The concurrency guard reuses this exact pattern rather than introducing a new locking primitive. |

## 3. Scope

**In:** one new catalog entry (`hypercode.run_tests` → `operator-run-tests`, single-node flow); one new local tool `backend/app/broski_operator/test_tools.py` (`local.run_tests`); one new Celery task `run_backend_tests` in `app/worker.py`, routed to `main-queue`; a Redis-backed concurrency lock; an explicit suite allow-list; the `pytest-json-report` dependency; unit tests; a new MCP tool `hypercode_run_tests`; a live-proof script.

**Out:** any non-`backend` test target (other agents live in separate containers/images `celery-worker` can't reach — `./backend` is the only thing it mounts); fixing the `hypercode-high/normal/low` vs `main-queue` routing gap; live sub-task progress reporting; any approval/gate node (this tool never needs human sign-off); any change to `hyperflow_runner.py` itself.

## 4. Design

### 4.1 Flow and catalog

```yaml
# backend/app/agents/hyperflow/flows/operator_run_tests.yml
name: operator-run-tests
version: 1
entry: run_tests
intent: "BROski operator: run the backend pytest suite asynchronously and report pass/fail counts"

nodes:
  - id: run_tests
    type: tool
    tool: local.run_tests
    idempotent: false   # a stale/duplicate dispatch would double-run tests, not just double-read

edges: []
```

`backend/app/broski_operator/catalog.py` gains `"hypercode.run_tests": "operator-run-tests"`.

### 4.2 Suite allow-list (default-deny, matching `recover`'s eligibility instinct)

```python
# backend/app/broski_operator/test_tools.py
SUITE_TARGETS: dict[str, str] = {
    "operator": "backend/tests/test_recover_core.py backend/tests/test_recover_policy.py "
                "backend/tests/test_recover_tools.py backend/tests/test_authorize_tools.py "
                "backend/tests/test_operator_tools.py backend/tests/test_operator_gate_context.py "
                "backend/tests/test_operator_plan_hash.py backend/tests/test_operator_mcp_tools.py "
                "backend/tests/test_flows_endpoint.py",
    "fast": "backend/tests/test_recover_policy.py",   # smallest real file; a quick liveness check
    "full": "backend/tests",
}
```

`suite` is a **required** string argument; anything not in this dict is rejected before Celery is ever touched (`{"ok": false, "error": "unknown suite"}`). No free-form paths are ever accepted — `celery-worker` only mounts `./backend`, so an arbitrary path string would be a code-execution surface, not a convenience.

### 4.3 Concurrency guard

```python
_LOCK_KEY = "hypercode:run_tests:lock"
_LOCK_TTL = 400  # past Celery's own 360s hard kill, so the lock always outlives the task

async def run_tests(params: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    suite = params.get("suite")
    target = SUITE_TARGETS.get(suite)
    if target is None:
        return {"ok": False, "error": "unknown suite", "allowed": sorted(SUITE_TARGETS)}

    run_id = str((ctx or {}).get("run_id", ""))
    r = aioredis.from_url(settings.HYPERCODE_REDIS_URL, decode_responses=True)
    try:
        got_lock = await r.set(_LOCK_KEY, run_id, nx=True, ex=_LOCK_TTL)
        if not got_lock:
            return {"ok": False, "busy": True}
        try:
            return await _dispatch_and_poll(suite, target)
        finally:
            await r.delete(_LOCK_KEY)
    finally:
        await r.aclose()


LOCAL_TOOLS["local.run_tests"] = run_tests  # registered in tools.py, matching every other local tool
```

A run already in flight makes a second call return `{"ok": false, "busy": true}` immediately — never queued, never silently dropped. This is the only thing standing between BROski and an OOM'd `celery-worker` from stacked full-suite runs, so it is unconditional and not configurable per-call.

### 4.4 Celery task

```python
# backend/app/worker.py
@celery_app.task(name="hypercode.tasks.run_backend_tests")
def run_backend_tests(target: str) -> dict:
    import json, subprocess, tempfile
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        report_path = f.name
    proc = subprocess.run(
        ["pytest", *target.split(), "-q", "--json-report", f"--json-report-file={report_path}"],
        capture_output=True, text=True, cwd="/app",
    )
    try:
        with open(report_path) as f:
            report = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"ok": False, "error": "no test report produced", "exit_code": proc.returncode,
                "stderr_tail": proc.stderr[-2000:]}
    summary = report.get("summary", {})
    return {
        "ok": proc.returncode == 0,
        "passed": summary.get("passed", 0),
        "failed": summary.get("failed", 0),
        "skipped": summary.get("skipped", 0),
        "duration_seconds": round(report.get("duration", 0.0), 1),
        "exit_code": proc.returncode,
    }
```

Routed via `celery_app.conf.task_routes["hypercode.tasks.run_backend_tests"] = {"queue": "main-queue"}` — the queue `celery-worker` actually consumes (see §2). Uses the worker's existing global `task_soft_time_limit`/`task_time_limit` (300s/360s) — no per-task override.

`_dispatch_and_poll` submits via `celery_app.send_task("hypercode.tasks.run_backend_tests", args=[target])`, then polls `AsyncResult.state` (wrapped in `asyncio.to_thread`, since the result-backend read is sync) every 2s. If the result isn't terminal by 400s, it calls `celery_app.control.revoke(task_id, terminate=True)` and returns `{"ok": false, "error": "timeout"}` — nothing is left silently running past the point BROski gave up watching it.

### 4.5 Result shape (persisted as this node's `result.data`, same convention as every other local tool)

```json
{"ok": true, "passed": 42, "failed": 0, "skipped": 1, "duration_seconds": 18.4, "suite": "operator"}
```

### 4.6 MCP tool

```python
@mcp.tool()
async def hypercode_run_tests(suite: str = "operator") -> dict:
    """
    Start the backend test suite as a background task (suite: "operator", "fast", or "full").
    Runs in celery-worker, never touches production data (tests use an isolated SQLite DB).
    Returns a task handle immediately; poll with hypercode_task_get.
    """
    return await _post(
        f"{API_PREFIX}/operator/tasks", {"tool": "hypercode.run_tests", "arguments": {"suite": suite}}
    )
```

## 5. Safety properties (each pinned by a test)

1. An unlisted `suite` value is rejected before any Redis or Celery call is made.
2. A second call while one run is in flight returns `{"busy": true}` and never dispatches a second Celery task.
3. The suite never touches `HYPERCODE_DB_URL` / the live Postgres — enforced by `conftest.py`'s existing SQLite override, not by anything this tool adds; a test asserts the task's subprocess environment carries no live DB credential override.
4. A task that never reaches a terminal state by the timeout is explicitly revoked (`terminate=True`), never left orphaned.
5. The Redis lock is always released (`finally`), including on a timeout or an exception from `_dispatch_and_poll`.
6. A malformed/missing JSON report (crash before pytest could write one) is reported as a structured failure, never raises out of the tool.

## 6. Testing

Unit (`backend/tests/test_run_tests_tool.py`): unknown suite → rejected, no Redis/Celery calls made (asserted via mock call counts); lock held by another run_id → `busy: true`, no `send_task` call; mocked `AsyncResult` reaching `SUCCESS` with a canned result dict → tool returns the parsed counts; mocked `AsyncResult` stuck in `PENDING` past the timeout → `revoke(terminate=True)` called once, tool returns `{"ok": false, "error": "timeout"}`; lock is released in both the success and timeout paths (`EXISTS` check after the call). Separate unit tests for `run_backend_tests` itself (`backend/tests/test_run_backend_tests_task.py`), run against a tiny two-test fixture file bundled under `backend/tests/fixtures/`, not the real suite recursively — asserting the JSON-report parse produces the right counts and that a report-file failure degrades to the structured-failure shape.

## 7. Live proof (real containers, no mocks)

Under the same RAM rules as every prior phase (`available` ≥ 1.2GB always, ≥ 1.5GB before any build; build only what changed; `up -d --no-deps`; never `--force-recreate`):

1. `scripts/prove-run-tests.py`, run inside `hypercode-core` against the real `celery-worker`: dispatch `suite: "operator"` via the real `/api/v1/operator/tasks` endpoint, poll the real task API to `completed`, assert `passed > 0` and `failed == 0` for this repo's own already-green test files.
2. While that run is in flight, fire a second `suite: "fast"` call → assert `{"busy": true}`.
3. Confirm `celery-worker` and `hypercode-core` both stay healthy, restart count 0, throughout.
4. Record available RAM before/during/after, per the established operating rule.

## 8. Known limitations / deferred (not fixed in this increment)

- No live sub-task progress — only `0%`/`100%` at the flow level (§2).
- The `hypercode-high/normal/low` vs `main-queue` routing gap is unrelated pre-existing debt, named here but not fixed; worth its own follow-up.
- `suite: "full"` may legitimately hit Celery's global 360s hard limit on this box — that's an acceptable, non-destructive failure (task fails cleanly, no OOM, no orphaned process), not something this increment works around with a special-cased longer limit.
- No non-backend suites (frontend, other agents) — `celery-worker` can't reach them (different images/containers); a future increment would need its own dispatch target per language/runtime.

## 9. Open items for review

1. Confirm the `SUITE_TARGETS["operator"]` file list in §4.2 is the right curated set — it's every test file touched by Phases 1/2a/2b; adjust if something's missing or shouldn't be in the routine "operator" check.
2. Confirm `pytest-json-report` as a new dependency is acceptable (vs. regex-parsing stdout, rejected in §2 for fragility).
