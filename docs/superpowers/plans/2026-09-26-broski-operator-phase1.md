# BROski Operator Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give BROski a durable, cancellable, approval-aware async task API (`/api/v1/operator/tasks`) plus MCP tools, backed by HyperFlow runs, with a real read-only `hypercode.inspect` tool proven live.

**Architecture:** A thin MCP-Tasks-shaped facade (`app/api/v1/endpoints/operator_tasks.py`) over the existing `HyperFlowRun` table and `HyperFlowRunner`. The runner gains cancel, context-preserving persistence, DB-backed approval decisions and restart recovery. `inspect` runs as an in-core "local tool" node (no orchestrator, no mock fallback). `hypercode-mcp-server` exposes the new endpoints as MCP tools.

**Tech Stack:** Python 3.13 / FastAPI / SQLAlchemy (Postgres prod, SQLite in tests) / Redis (existing DB 1 cache + pub/sub) / pytest (`asyncio.run` style, no pytest-asyncio needed) / FastMCP (`mcp` 1.27.1 in the MCP server image).

**Spec:** `docs/superpowers/specs/2026-09-26-broski-operator-design.md` (amendments made while planning are listed in Task 7).

## Global Constraints

- Python: 4-space indent, never 3, never mixed. Imports are `from app.X import Y`, never `from backend.app.X`.
- **No DB migration.** `hyperflow_runs.status` is `String(24)`; only the Python enum gains `CANCELLED`.
- Redis DB 1 is cache-only. Task truth lives in Postgres (`hyperflow_runs.state` JSONB). Never use Redis as the durable record.
- Task status vocabulary is exactly: `working`, `input_required`, `completed`, `failed`, `cancelled`.
- Mapping: `running→working`, `awaiting_approval→input_required`, others pass through.
- **Approvals require a human JWT.** An agent key (`X-Agent-Key`) can start, read and cancel tasks but can never submit an approval decision.
- The core process runs a **single uvicorn worker** (runner comment: multi-worker resume is future work). `recover_runs()` is not multi-worker safe.
- Never print an env var value. Never run `docker compose config` after a secret change. Never `--force-recreate` near `hypercode-core`. Never `--remove-orphans`.
- Only run the new/named test files with pytest, never the whole repo suite (box OOM-kills, see WHATS_DONE N22). First run of any test file can take ~2 min (app import).
- Work only on branch `feature/broski-operator` in `H:\HYPERFOCUSZONE\HperCore\HyperCode-V2.4`. Commit prefixes `feat:` / `fix:` / `docs:` / `chore:`. Every commit message ends with the line `Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>`. `git fetch` before any push, never force-push, **do not push without Bro's say-so**.
- Run pytest from the `backend/` directory: `cd backend && python -m pytest <file> -v -p no:cacheprovider`.
- New tests must be network-free: every test file that runs a runner adds the autouse fixture that sets `SAFETY_SHEPHERD_MODE=off`.

## Review Focus

The spec is silent on these; each is pinned by a named test in the owning task.

1. **Loop shutdown must not cancel runs.** When core stops, asyncio cancels the runner task. That must leave the run `running` so `recover_runs()` can resume it, not mark it `cancelled` (Task 1).
2. **A stale or duplicate approval must never approve a later gate.** A decision is consumed on read; `/input` is refused unless the run is awaiting approval; a second decision while one is pending is refused (Tasks 2, 5).
3. **An agent key must not be able to approve** (Task 5, 403 test).
4. **Unknown tool names and non-empty `arguments` are rejected**, never silently ignored (Task 5).
5. **`inspect` with dependencies down or hanging returns a structured report**, never an exception or a hang (Task 4).
6. A path-injection style `task_id` passed through the MCP tools is rejected before any HTTP call (Task 6).
7. A run whose flow file was later deleted or renamed is failed cleanly at recovery, not crashed on (Task 3).

## File Structure

| File | Responsibility |
|---|---|
| `backend/app/models/hyperflow.py` (modify) | add `CANCELLED` status |
| `backend/app/agents/hyperflow/schema.py` (modify) | `FlowNode.idempotent` flag |
| `backend/app/agents/hyperflow_runner.py` (modify) | cancel, merge-persist, `history`/`start_at`, DB decisions, local tool dispatch |
| `backend/app/broski_operator/__init__.py` (create) | package marker |
| `backend/app/broski_operator/status.py` (create) | pure status/progress/result mapping |
| `backend/app/broski_operator/catalog.py` (create) | tool-name → flow-name allow-list |
| `backend/app/broski_operator/runs.py` (create) | DB helpers taking an explicit `Session` |
| `backend/app/broski_operator/recovery.py` (create) | `plan_recovery` (pure) + `recover_runs` |
| `backend/app/broski_operator/tools.py` (create) | local tool registry + `inspect_stack` |
| `backend/app/agents/hyperflow/flows/operator_inspect.yml` (create) | one-node inspect flow |
| `backend/app/api/v1/endpoints/operator_tasks.py` (create) | `/operator/tasks` routes + principal dependency |
| `backend/app/api/api.py` (modify) | mount router at `/operator` |
| `backend/app/main.py` (modify) | call `recover_runs()` in lifespan |
| `services/hypercode-mcp-server/server.py` (modify) | MCP tools + agent-key header |
| `docker-compose.agents.yml` (modify) | `HYPERCODE_AGENT_KEY` env for the MCP server |
| `scripts/prove-operator.py` (create) | live proof, runs inside `hypercode-core` |
| `backend/tests/conftest.py` (modify) | `hf_db` fixture |
| `backend/tests/operator_helpers.py` (create) | shared tiny flow builders |
| `backend/tests/test_hyperflow.py` (modify, 1 line) | patch persisted-decision read in the shared runner helper |
| `backend/tests/test_operator_*.py` (create) | one test file per task |

---

### Task 1: Runner cancel + context-preserving persistence

**Files:**
- Modify: `backend/app/models/hyperflow.py` (enum)
- Modify: `backend/app/agents/hyperflow_runner.py` (`__init__`, `_run`, `_persist_sync`, new `cancel`)
- Modify: `backend/tests/conftest.py` (append `hf_db` fixture)
- Create: `backend/tests/operator_helpers.py`
- Test: `backend/tests/test_operator_runner.py`

**Interfaces:**
- Produces: `HyperFlowRunStatus.CANCELLED = "cancelled"`.
- Produces: `HyperFlowRunner(flow, run_id, *, user_id=None, history: Optional[list[dict]] = None)`.
- Produces: `async HyperFlowRunner.cancel(reason: str = "cancelled") -> bool` (False if the run is not live in this process).
- Produces: `_persist_sync` now preserves every key already in `state` (notably `context`) and only overwrites `history` / `error`.
- Produces: fixture `hf_db` → a `sessionmaker` bound to an in-memory SQLite that holds only `hyperflow_runs`; patched into `app.agents.hyperflow_runner.SessionLocal`.
- Produces: `tests/operator_helpers.py::gate_flow(name="g")` (single `human_approval_gate` node `gate`) and `two_gate_flow()` (gates `a` → `b`).

- [ ] **Step 1: Add the enum member**

In `backend/app/models/hyperflow.py` change the enum to:

```python
class HyperFlowRunStatus(str, enum.Enum):
    RUNNING            = "running"
    AWAITING_APPROVAL  = "awaiting_approval"
    COMPLETED          = "completed"
    FAILED             = "failed"
    CANCELLED          = "cancelled"
```

- [ ] **Step 2: Append the `hf_db` fixture to `backend/tests/conftest.py`**

Add at the end of the file (`create_engine`, `sessionmaker` and `pytest` are already imported there):

```python
@pytest.fixture
def hf_db(monkeypatch):
    """In-memory SQLite holding only ``hyperflow_runs``, patched into the HyperFlow runner."""
    from sqlalchemy.pool import StaticPool

    from app.models.hyperflow import HyperFlowRun

    eng = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    HyperFlowRun.__table__.create(bind=eng)
    factory = sessionmaker(bind=eng, autoflush=False, autocommit=False)
    monkeypatch.setattr("app.agents.hyperflow_runner.SessionLocal", factory)
    yield factory
    eng.dispose()
```

- [ ] **Step 3: Create `backend/tests/operator_helpers.py`**

```python
"""Tiny flow builders shared by the BROski operator tests."""

from app.agents.hyperflow.schema import FlowDefinition


def gate_flow(name: str = "g") -> FlowDefinition:
    """One human_approval_gate node called ``gate``."""
    return FlowDefinition.model_validate(
        {
            "name": name,
            "entry": "gate",
            "nodes": [{"id": "gate", "type": "human_approval_gate", "params": {"prompt": "ok?"}}],
        }
    )


def two_gate_flow() -> FlowDefinition:
    """Gate ``a`` then gate ``b``."""
    return FlowDefinition.model_validate(
        {
            "name": "two",
            "entry": "a",
            "nodes": [
                {"id": "a", "type": "human_approval_gate", "params": {"prompt": "a?"}},
                {"id": "b", "type": "human_approval_gate", "params": {"prompt": "b?"}},
            ],
            "edges": [{"from": "a", "to": "b"}],
        }
    )
```

- [ ] **Step 4: Write the failing tests** — `backend/tests/test_operator_runner.py`

```python
"""BROski operator — runner changes: cancel + context-preserving persistence."""

import asyncio

import pytest

from app.agents.hyperflow_runner import HyperFlowRunner
from app.models.hyperflow import HyperFlowRun, HyperFlowRunStatus
from tests.operator_helpers import gate_flow
from tests.test_hyperflow import _runner_with_io


@pytest.fixture(autouse=True)
def _safety_off(monkeypatch):
    monkeypatch.setenv("SAFETY_SHEPHERD_MODE", "off")


def test_cancel_status_exists():
    assert HyperFlowRunStatus.CANCELLED.value == "cancelled"


def test_cancel_live_run_marks_cancelled(monkeypatch):
    runner, final = _runner_with_io(gate_flow(), "c1", monkeypatch)

    async def scenario():
        runner._task = asyncio.create_task(runner._run())
        await asyncio.sleep(0.05)  # let it park at the approval gate
        assert await runner.cancel("stop it") is True

    asyncio.run(scenario())
    assert final["status"] is HyperFlowRunStatus.CANCELLED
    assert final["error"] == "stop it"


def test_cancel_without_live_task_returns_false():
    runner = HyperFlowRunner(gate_flow(), "c2")
    assert asyncio.run(runner.cancel("nobody home")) is False


def test_loop_shutdown_cancel_leaves_run_recoverable(monkeypatch):
    """Review focus 1: a bare task.cancel() (loop shutdown) must NOT mark the run cancelled."""
    runner, final = _runner_with_io(gate_flow(), "c3", monkeypatch)

    async def scenario():
        task = asyncio.create_task(runner._run())
        await asyncio.sleep(0.05)
        task.cancel()  # no runner.cancel(): no reason recorded
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
    assert "status" not in final


def test_persist_preserves_context_and_updates_history(hf_db):
    runner = HyperFlowRunner(gate_flow(), "p1")
    runner._persist_sync(HyperFlowRunStatus.RUNNING, "gate", False, None)

    s = hf_db()
    run = s.get(HyperFlowRun, "p1")
    run.state = {**run.state, "context": {"pending_decision": {"approved": True}}}
    s.commit()
    s.close()

    runner._history.append({"node": "gate", "status": "completed"})
    runner._persist_sync(HyperFlowRunStatus.RUNNING, "gate", False, None)

    s = hf_db()
    run = s.get(HyperFlowRun, "p1")
    assert run.state["context"]["pending_decision"] == {"approved": True}
    assert run.state["history"] == [{"node": "gate", "status": "completed"}]
    s.close()
```

- [ ] **Step 5: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_operator_runner.py -v -p no:cacheprovider`
Expected: FAIL (`AttributeError: ... has no attribute 'cancel'`, and the persist test fails because `context` is wiped).

- [ ] **Step 6: Implement in `backend/app/agents/hyperflow_runner.py`**

6a. Extend `__init__` (add the `history` kwarg and `_cancel_reason`):

```python
    def __init__(
        self,
        flow: FlowDefinition,
        run_id: str,
        *,
        user_id: Optional[int] = None,
        history: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        self.flow = flow
        self.run_id = run_id
        self.user_id = user_id
        self._history: list[dict[str, Any]] = list(history or [])
        self._approval_event = asyncio.Event()
        self._approval_result: Optional[bool] = None
        self._task: Optional[asyncio.Task] = None
        self._cancel_reason: Optional[str] = None
        self._cache_url = cache_redis_url()
```

6b. Add the `cancel` method directly after `resume`:

```python
    async def cancel(self, reason: str = "cancelled") -> bool:
        """Cancel a live run. Returns False when it is not running in this process."""
        task = self._task
        if task is None or task.done():
            return False
        self._cancel_reason = reason
        task.cancel()
        await asyncio.wait({task}, timeout=5.0)
        return True
```

6c. In `_run`, add the cancellation handler between `except _FlowFailed` and `except Exception` (asyncio.CancelledError is a BaseException, so it is not caught by `except Exception`):

```python
        except asyncio.CancelledError:
            if self._cancel_reason is None:
                # Event-loop shutdown, not an operator cancel: leave the run 'running'
                # so recover_runs() can resume it after the restart.
                raise
            await self._finish(HyperFlowRunStatus.CANCELLED, error=self._cancel_reason)
```

6d. Replace the body of `_persist_sync` so it merges into existing state instead of replacing it:

```python
    def _persist_sync(
        self,
        status: HyperFlowRunStatus,
        current_node: Optional[str],
        completed: bool,
        error: Optional[str],
    ) -> None:
        db = SessionLocal()
        try:
            run = db.get(HyperFlowRun, self.run_id)
            if run is None:
                state: dict[str, Any] = {"history": self._history}
                if error:
                    state["error"] = error
                run = HyperFlowRun(
                    id=self.run_id,
                    flow_name=self.flow.name,
                    flow_version=self.flow.version,
                    status=status.value,
                    current_node=current_node,
                    state=state,
                )
                db.add(run)
            else:
                # Merge: keep everything else in state (e.g. ``context`` written by the
                # operator API) and only refresh history / error.
                state = dict(run.state or {})
                state["history"] = self._history
                if error:
                    state["error"] = error
                run.status = status.value
                run.current_node = current_node
                run.state = state
                if completed:
                    run.completed_at = datetime.now(timezone.utc)
            db.commit()
        except Exception:  # pragma: no cover — never let persistence kill the run
            db.rollback()
            logger.exception("hyperflow %s persist failed", self.run_id)
        finally:
            db.close()
```

- [ ] **Step 7: Run to verify pass, plus the existing runner tests**

Run: `cd backend && python -m pytest tests/test_operator_runner.py tests/test_hyperflow.py -v -p no:cacheprovider`
Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/hyperflow.py backend/app/agents/hyperflow_runner.py backend/tests/conftest.py backend/tests/operator_helpers.py backend/tests/test_operator_runner.py
git commit -m "feat: HyperFlow runner cancel + context-preserving persistence

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 2: Durable approval decisions + start-at-node

**Files:**
- Modify: `backend/app/agents/hyperflow_runner.py` (`_run` signature, new `start_at`, `_take_persisted_decision`, `_await_approval`, constant)
- Modify: `backend/tests/test_hyperflow.py` (one line in `_runner_with_io`)
- Test: `backend/tests/test_operator_durable_approval.py`

**Interfaces:**
- Consumes (Task 1): `HyperFlowRunner(..., history=...)`, `hf_db`, `gate_flow`, `two_gate_flow`.
- Produces: `APPROVAL_POLL_SECONDS` module constant (env `HYPERFLOW_APPROVAL_POLL_SECONDS`, default `2`).
- Produces: `HyperFlowRunner._take_persisted_decision() -> Optional[bool]` (sync; reads then clears `state.context.pending_decision`, returns its `approved` bool or `None`).
- Produces: `async HyperFlowRunner.start_at(node_id: str) -> HyperFlowRunner` (re-attach to a persisted run and continue from `node_id`).
- Produces: `HyperFlowRunner._run(start_at: Optional[str] = None)`.
- Contract for later tasks: the operator API stores the decision as `state["context"]["pending_decision"] = {"approved": bool, "by": str, "ts": iso}`.

- [ ] **Step 1: Patch the shared helper so existing gate tests never touch a real DB**

In `backend/tests/test_hyperflow.py`, inside `_runner_with_io`, add this line directly after the existing `monkeypatch.setattr(runner, "_publish_approval_request", _noop)`:

```python
    monkeypatch.setattr(runner, "_take_persisted_decision", lambda: None)
```

- [ ] **Step 2: Write the failing tests** — `backend/tests/test_operator_durable_approval.py`

```python
"""BROski operator — approvals survive restarts; runs can start mid-graph."""

import asyncio

import pytest

from app.models.hyperflow import HyperFlowRun, HyperFlowRunStatus
from app.agents.hyperflow_runner import HyperFlowRunner
from tests.operator_helpers import gate_flow, two_gate_flow
from tests.test_hyperflow import _runner_with_io


@pytest.fixture(autouse=True)
def _safety_off(monkeypatch):
    monkeypatch.setenv("SAFETY_SHEPHERD_MODE", "off")
    monkeypatch.setattr("app.agents.hyperflow_runner.APPROVAL_POLL_SECONDS", 0.01)


def _seed(factory, run_id, decision=None, extra_context=None):
    state = {"history": []}
    ctx = dict(extra_context or {})
    if decision is not None:
        ctx["pending_decision"] = {"approved": decision, "by": "test", "ts": "t"}
    if ctx:
        state["context"] = ctx
    s = factory()
    s.add(
        HyperFlowRun(
            id=run_id, flow_name="g", flow_version=1,
            status="awaiting_approval", current_node="gate", state=state,
        )
    )
    s.commit()
    s.close()


def test_gate_honours_persisted_approval(monkeypatch):
    runner, final = _runner_with_io(gate_flow(), "d1", monkeypatch)
    calls = {"n": 0}

    def _take():
        calls["n"] += 1
        return True if calls["n"] >= 2 else None

    monkeypatch.setattr(runner, "_take_persisted_decision", _take)
    asyncio.run(runner._run())
    assert final["status"] is HyperFlowRunStatus.COMPLETED


def test_gate_honours_persisted_rejection(monkeypatch):
    runner, final = _runner_with_io(gate_flow(), "d2", monkeypatch)
    monkeypatch.setattr(runner, "_take_persisted_decision", lambda: False)
    asyncio.run(runner._run())
    assert final["status"] is HyperFlowRunStatus.FAILED
    assert "approval rejected" in final["error"]


def test_in_memory_resume_still_works(monkeypatch):
    """The legacy /flows/runs/{id}/resume path signals the event; it must still complete."""
    runner, final = _runner_with_io(gate_flow(), "d3", monkeypatch)

    async def scenario():
        runner._task = asyncio.create_task(runner._run())
        await asyncio.sleep(0.05)
        runner.resume(True)
        await runner._task

    asyncio.run(scenario())
    assert final["status"] is HyperFlowRunStatus.COMPLETED


def test_take_persisted_decision_consumes_and_keeps_other_context(hf_db):
    _seed(hf_db, "d4", decision=True, extra_context={"keep": 1})
    runner = HyperFlowRunner(gate_flow(), "d4")
    assert runner._take_persisted_decision() is True
    assert runner._take_persisted_decision() is None  # Review focus 2: consumed once only
    s = hf_db()
    ctx = s.get(HyperFlowRun, "d4").state["context"]
    s.close()
    assert ctx == {"keep": 1}


def test_take_persisted_decision_no_row_returns_none(hf_db):
    assert HyperFlowRunner(gate_flow(), "missing")._take_persisted_decision() is None


def test_run_can_start_at_a_given_node(monkeypatch):
    runner, final = _runner_with_io(two_gate_flow(), "s1", monkeypatch)
    monkeypatch.setattr(runner, "_take_persisted_decision", lambda: True)
    asyncio.run(runner._run("b"))
    assert [e["node"] for e in runner._history] == ["b", "b"]  # awaiting_approval + completed
    assert final["status"] is HyperFlowRunStatus.COMPLETED
```

- [ ] **Step 3: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_operator_durable_approval.py -v -p no:cacheprovider`
Expected: FAIL (`AttributeError: ... APPROVAL_POLL_SECONDS` / `_take_persisted_decision`).

- [ ] **Step 4: Implement in `backend/app/agents/hyperflow_runner.py`**

4a. Add the constant next to `APPROVAL_CHANNEL`:

```python
# How often a parked approval gate re-checks Postgres for a decision that was written
# while this process was down (or by another process). Seconds.
APPROVAL_POLL_SECONDS = float(os.getenv("HYPERFLOW_APPROVAL_POLL_SECONDS", "2"))
```

4b. Add `start_at` after `start`:

```python
    async def start_at(self, node_id: str) -> "HyperFlowRunner":
        """Re-attach to a persisted run (see recovery.recover_runs) and continue from ``node_id``."""
        _ACTIVE[self.run_id] = self
        self._task = asyncio.create_task(self._run(node_id))
        return self
```

4c. Change `_run`'s signature and first lines:

```python
    async def _run(self, start_at: Optional[str] = None) -> None:
        loop_counts: dict[tuple[str, str], int] = {}
        node_id: Optional[str] = start_at or self.flow.entry
```

4d. Add `_take_persisted_decision` (place it just above `_await_approval`):

```python
    def _take_persisted_decision(self) -> Optional[bool]:
        """Read and clear ``state.context.pending_decision`` written by the operator API."""
        db = SessionLocal()
        try:
            run = db.get(HyperFlowRun, self.run_id)
            if run is None:
                return None
            state = dict(run.state or {})
            ctx = dict(state.get("context") or {})
            decision = ctx.pop("pending_decision", None)
            if decision is None:
                return None
            state["context"] = ctx
            run.state = state
            db.commit()
            return bool(decision.get("approved"))
        except Exception:  # pragma: no cover — a DB blip must not kill the run
            db.rollback()
            logger.exception("hyperflow %s decision read failed", self.run_id)
            return None
        finally:
            db.close()
```

4e. Replace `_await_approval`:

```python
    async def _await_approval(self, node: FlowNode) -> dict[str, Any]:
        self._approval_event.clear()
        self._approval_result = None
        prompt = node.params.get("prompt", f"Approve step '{node.id}'?")
        await self._emit(node, "awaiting_approval", {"prompt": prompt},
                         HyperFlowRunStatus.AWAITING_APPROVAL)
        await self._publish_approval_request(node, prompt)
        while True:
            # A decision may already be waiting (written while this process was down).
            persisted = await asyncio.to_thread(self._take_persisted_decision)
            if persisted is not None:
                self._approval_result = persisted
                break
            try:
                await asyncio.wait_for(self._approval_event.wait(), timeout=APPROVAL_POLL_SECONDS)
            except asyncio.TimeoutError:
                continue
            # Woken by the in-memory resume(): drop any duplicate persisted decision.
            await asyncio.to_thread(self._take_persisted_decision)
            break
        if not self._approval_result:
            raise _ApprovalRejected(node.id)
        return {"ok": True, "approved": True}
```

- [ ] **Step 5: Run to verify pass, plus existing runner tests**

Run: `cd backend && python -m pytest tests/test_operator_durable_approval.py tests/test_operator_runner.py tests/test_hyperflow.py -v -p no:cacheprovider`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/agents/hyperflow_runner.py backend/tests/test_hyperflow.py backend/tests/test_operator_durable_approval.py
git commit -m "feat: durable HyperFlow approvals (DB-backed decision) + start_at

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 3: Restart recovery (`plan_recovery`, `recover_runs`, lifespan hook)

**Files:**
- Modify: `backend/app/agents/hyperflow/schema.py` (`FlowNode.idempotent`)
- Create: `backend/app/broski_operator/__init__.py`, `runs.py`, `recovery.py`
- Modify: `backend/app/main.py` (lifespan, before `yield`)
- Modify: `backend/tests/conftest.py` (extend `hf_db` to also patch recovery's `SessionLocal`)
- Test: `backend/tests/test_operator_recovery.py`

**Interfaces:**
- Consumes (Tasks 1–2): `HyperFlowRunner(flow, run_id, history=...)`, `start_at(node_id)`, `_next_node`.
- Produces: `FlowNode.idempotent: bool = False`.
- Produces (`runs.py`, every function takes an explicit `Session`):
  - `OPEN_STATUSES: tuple[str, ...]`
  - `load_open_runs(db) -> list[tuple[str, str, str, list[dict]]]` — `(run_id, flow_name, status, history)`
  - `store_decision(db, run, *, approved: bool, by: str) -> bool` — `False` if a decision is already pending
  - `finish_run_row(db, run, status: HyperFlowRunStatus, error: Optional[str]) -> None`
- Produces (`recovery.py`):
  - `@dataclass(frozen=True) RecoveryPlan(action: str, node_id: Optional[str] = None, reason: str = "")` with `action ∈ {"resume","complete","fail","skip"}`
  - `plan_recovery(flow, status: str, history: list[dict]) -> RecoveryPlan`
  - `async recover_runs() -> dict[str, int]` (counts per action)

- [ ] **Step 1: Add the schema flag**

In `backend/app/agents/hyperflow/schema.py`, add one field to `FlowNode` after `safety`:

```python
    # Recovery: True = safe to re-run this node after a core restart interrupted it.
    idempotent: bool = False
```

- [ ] **Step 2: Create `backend/app/broski_operator/__init__.py`**

```python
"""BROski operator: durable async tasks on top of HyperFlow (spec 2026-09-26)."""
```

- [ ] **Step 3: Extend the `hf_db` fixture** in `backend/tests/conftest.py` — add one line after the existing `monkeypatch.setattr(... hyperflow_runner.SessionLocal ...)`:

```python
    monkeypatch.setattr("app.broski_operator.recovery.SessionLocal", factory)
```

- [ ] **Step 4: Write the failing tests** — `backend/tests/test_operator_recovery.py`

```python
"""BROski operator — restart recovery + DB helpers."""

import asyncio

import pytest

from app.agents.hyperflow.schema import FlowDefinition
from app.agents.hyperflow_runner import HyperFlowRunner
from app.broski_operator import recovery, runs
from app.broski_operator.recovery import RecoveryPlan, plan_recovery, recover_runs
from app.models.hyperflow import HyperFlowRun, HyperFlowRunStatus

FLOW = FlowDefinition.model_validate(
    {
        "name": "f",
        "entry": "a",
        "nodes": [
            {"id": "a", "type": "tool", "tool": "local.x", "idempotent": True},
            {"id": "b", "type": "tool", "tool": "t.b"},
            {"id": "c", "type": "human_approval_gate"},
        ],
        "edges": [{"from": "a", "to": "b"}, {"from": "b", "to": "c"}],
    }
)
NON_IDEMPOTENT_ENTRY = FlowDefinition.model_validate(
    {"name": "n", "entry": "b", "nodes": [{"id": "b", "type": "tool", "tool": "t.b"}]}
)


def _done(node, success=True):
    return {"node": node, "type": "tool", "status": "completed", "result": {"success": success}}


def test_only_open_statuses_are_planned():
    assert plan_recovery(FLOW, "completed", []).action == "skip"
    assert plan_recovery(FLOW, "cancelled", []).action == "skip"


def test_empty_history_resumes_idempotent_entry():
    assert plan_recovery(FLOW, "running", []) == RecoveryPlan("resume", "a", "next node is safe to re-run")


def test_empty_history_fails_non_idempotent_entry():
    plan = plan_recovery(NON_IDEMPOTENT_ENTRY, "running", [])
    assert plan.action == "fail" and plan.node_id == "b"


def test_next_node_not_idempotent_fails():
    plan = plan_recovery(FLOW, "running", [_done("a")])
    assert plan.action == "fail" and "not idempotent" in plan.reason


def test_next_node_gate_resumes():
    assert plan_recovery(FLOW, "running", [_done("a"), _done("b")]).node_id == "c"


def test_terminal_last_node_completes():
    assert plan_recovery(FLOW, "running", [_done("a"), _done("b"), _done("c")]).action == "complete"


def test_parked_at_gate_resumes_at_the_gate():
    hist = [{"node": "c", "type": "human_approval_gate", "status": "awaiting_approval", "result": {}}]
    plan = plan_recovery(FLOW, "awaiting_approval", hist)
    assert plan == RecoveryPlan("resume", "c", "parked at approval gate")


def test_failed_last_entry_fails_run():
    hist = [{"node": "b", "type": "tool", "status": "failed", "result": {}}]
    assert plan_recovery(FLOW, "running", hist).action == "fail"


def _add(factory, run_id, flow_name, status, history):
    s = factory()
    s.add(HyperFlowRun(id=run_id, flow_name=flow_name, flow_version=1, status=status,
                       current_node=None, state={"history": history}))
    s.commit()
    s.close()


def test_recover_runs_resumes_fails_and_leaves_terminal_alone(hf_db, monkeypatch):
    started = []

    async def _fake_start_at(self, node_id):
        started.append((self.run_id, node_id, len(self._history)))
        return self

    monkeypatch.setattr(HyperFlowRunner, "start_at", _fake_start_at)
    gate_hist = [{"node": "ready", "type": "human_approval_gate",
                  "status": "awaiting_approval", "result": {}}]
    _add(hf_db, "r-gate", "hyperflow-smoke", "awaiting_approval", gate_hist)
    _add(hf_db, "r-ghost", "vanished-flow", "running", [])  # Review focus 7
    _add(hf_db, "r-done", "hyperflow-smoke", "completed", [])
    _add(hf_db, "r-cancelled", "hyperflow-smoke", "cancelled", [])

    counts = asyncio.run(recover_runs())

    assert counts == {"resume": 1, "complete": 0, "fail": 1, "skip": 0}
    assert started == [("r-gate", "ready", 1)]
    s = hf_db()
    ghost = s.get(HyperFlowRun, "r-ghost")
    assert ghost.status == "failed" and "no longer exists" in ghost.state["error"]
    assert s.get(HyperFlowRun, "r-done").status == "completed"
    assert s.get(HyperFlowRun, "r-cancelled").status == "cancelled"
    s.close()


def test_store_decision_once_then_refuses(hf_db):
    _add(hf_db, "sd", "hyperflow-smoke", "awaiting_approval", [])
    s = hf_db()
    run = s.get(HyperFlowRun, "sd")
    assert runs.store_decision(s, run, approved=True, by="bro") is True
    assert run.state["context"]["pending_decision"]["approved"] is True
    assert runs.store_decision(s, run, approved=False, by="bro") is False
    s.close()


def test_finish_run_row_records_terminal_entry(hf_db):
    _add(hf_db, "fr", "hyperflow-smoke", "running", [{"node": "x", "status": "completed"}])
    s = hf_db()
    run = s.get(HyperFlowRun, "fr")
    runs.finish_run_row(s, run, HyperFlowRunStatus.CANCELLED, "because")
    s.close()
    s = hf_db()
    run = s.get(HyperFlowRun, "fr")
    assert run.status == "cancelled" and run.completed_at is not None
    assert run.state["error"] == "because"
    assert run.state["history"][-1]["type"] == "terminal"
    assert run.state["history"][-1]["status"] == "cancelled"
    s.close()
```

- [ ] **Step 5: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_operator_recovery.py -v -p no:cacheprovider`
Expected: FAIL (`ModuleNotFoundError: app.broski_operator.recovery`).

- [ ] **Step 6: Create `backend/app/broski_operator/runs.py`**

```python
"""DB helpers for operator-managed HyperFlow runs. Every function takes an explicit Session."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.hyperflow import HyperFlowRun, HyperFlowRunStatus

OPEN_STATUSES = (
    HyperFlowRunStatus.RUNNING.value,
    HyperFlowRunStatus.AWAITING_APPROVAL.value,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_open_runs(db: Session) -> list[tuple[str, str, str, list[dict[str, Any]]]]:
    """(run_id, flow_name, status, history) for every run that was live when we stopped."""
    rows = db.query(HyperFlowRun).filter(HyperFlowRun.status.in_(OPEN_STATUSES)).all()
    return [
        (r.id, r.flow_name, r.status, list((r.state or {}).get("history", [])))
        for r in rows
    ]


def store_decision(db: Session, run: HyperFlowRun, *, approved: bool, by: str) -> bool:
    """Persist an approval decision for the runner to pick up. False if one is already pending."""
    state = dict(run.state or {})
    ctx = dict(state.get("context") or {})
    if "pending_decision" in ctx:
        return False
    ctx["pending_decision"] = {"approved": approved, "by": by, "ts": _now()}
    state["context"] = ctx
    run.state = state
    db.commit()
    return True


def finish_run_row(
    db: Session,
    run: HyperFlowRun,
    status: HyperFlowRunStatus,
    error: Optional[str],
) -> None:
    """Terminate a run directly in Postgres (used when no live runner owns it)."""
    state = dict(run.state or {})
    history = list(state.get("history", []))
    history.append(
        {
            "node": None,
            "type": "terminal",
            "status": status.value,
            "result": {"error": error} if error else {},
            "ts": _now(),
        }
    )
    state["history"] = history
    if error:
        state["error"] = error
    run.state = state
    run.status = status.value
    run.current_node = None
    run.completed_at = datetime.now(timezone.utc)
    db.commit()
```

- [ ] **Step 7: Create `backend/app/broski_operator/recovery.py`**

```python
"""Restart recovery for HyperFlow runs (spec §5.2).

``plan_recovery`` is pure. ``recover_runs`` applies the plans at core startup.
Loop counters are not persisted, so a recovered run's loop budget restarts at zero
and the originating user id is not restored (recovered runs dispatch without one).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Optional

from app.agents.hyperflow.registry import get_flow
from app.agents.hyperflow.schema import FlowDefinition, NodeType
from app.agents.hyperflow_runner import HyperFlowRunner, get_runner
from app.broski_operator.runs import OPEN_STATUSES, finish_run_row, load_open_runs
from app.db.session import SessionLocal
from app.models.hyperflow import HyperFlowRun, HyperFlowRunStatus

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RecoveryPlan:
    action: str  # "resume" | "complete" | "fail" | "skip"
    node_id: Optional[str] = None
    reason: str = ""


def plan_recovery(flow: FlowDefinition, status: str, history: list[dict[str, Any]]) -> RecoveryPlan:
    """Decide what to do with a run that was live when core stopped."""
    if status not in OPEN_STATUSES:
        return RecoveryPlan("skip", reason=f"status={status}")

    last = history[-1] if history else None
    if last is None:
        next_id: Optional[str] = flow.entry
    elif last.get("status") == "awaiting_approval":
        return RecoveryPlan("resume", last["node"], "parked at approval gate")
    elif last.get("status") == "completed":
        node = flow.node(last["node"])
        success = bool((last.get("result") or {}).get("success", True))
        next_id = HyperFlowRunner(flow, "plan")._next_node(node, success, {})
        if next_id is None:
            return RecoveryPlan("complete", reason="last node was terminal")
    else:  # a failed entry: retry/fallback was in flight — do not guess
        return RecoveryPlan("fail", reason="interrupted by restart")

    node = flow.node(next_id)
    if node.type is NodeType.HUMAN_APPROVAL_GATE or node.idempotent:
        return RecoveryPlan("resume", next_id, "next node is safe to re-run")
    return RecoveryPlan(
        "fail", next_id, f"interrupted by restart: node '{next_id}' is not idempotent"
    )


def _finish_row(run_id: str, plan: RecoveryPlan) -> None:
    db = SessionLocal()
    try:
        run = db.get(HyperFlowRun, run_id)
        if run is None:
            return
        if plan.action == "complete":
            finish_run_row(db, run, HyperFlowRunStatus.COMPLETED, None)
        else:
            finish_run_row(db, run, HyperFlowRunStatus.FAILED, plan.reason)
    finally:
        db.close()


def _load() -> list[tuple[str, str, str, list[dict[str, Any]]]]:
    db = SessionLocal()
    try:
        return load_open_runs(db)
    finally:
        db.close()


async def recover_runs() -> dict[str, int]:
    """Re-attach runs that were live when core last stopped. Returns counts per action."""
    counts = {"resume": 0, "complete": 0, "fail": 0, "skip": 0}
    for run_id, flow_name, status, history in await asyncio.to_thread(_load):
        if get_runner(run_id) is not None:
            continue
        flow = get_flow(flow_name)
        if flow is None:
            plan = RecoveryPlan("fail", reason=f"flow '{flow_name}' no longer exists")
        else:
            plan = plan_recovery(flow, status, history)
        counts[plan.action] += 1
        if plan.action == "resume":
            assert flow is not None and plan.node_id is not None
            runner = HyperFlowRunner(flow, run_id, history=history)
            await runner.start_at(plan.node_id)
        elif plan.action in ("complete", "fail"):
            await asyncio.to_thread(_finish_row, run_id, plan)
        logger.info("hyperflow recovery run=%s action=%s reason=%s", run_id, plan.action, plan.reason)
    return counts
```

- [ ] **Step 8: Run to verify pass**

Run: `cd backend && python -m pytest tests/test_operator_recovery.py tests/test_operator_durable_approval.py tests/test_operator_runner.py -v -p no:cacheprovider`
Expected: all PASS.

- [ ] **Step 9: Hook into the lifespan**

In `backend/app/main.py`, inside `_lifespan`, in the `else:` branch directly after the telemetry `try/except` block (the one ending `logger.exception("Telemetry init failed (non-fatal)")`) and before the bare `yield`, add (8-space indent, same level as the neighbouring `try:` blocks):

```python
        try:
            from app.broski_operator.recovery import recover_runs as _recover_runs

            logger.info("HyperFlow recovery: %s", await _recover_runs())
        except Exception:
            logger.exception("HyperFlow recovery failed (non-fatal)")
```

- [ ] **Step 10: Verify the app still boots under the test client**

Run: `cd backend && python -m pytest tests/test_flows_endpoint.py tests/test_hyperflow.py -v -p no:cacheprovider`
Expected: PASS (the `client` fixture starts the lifespan; recovery must fail soft when the test DB has no open runs).

- [ ] **Step 11: Commit**

```bash
git add backend/app/agents/hyperflow/schema.py backend/app/broski_operator backend/app/main.py backend/tests/conftest.py backend/tests/test_operator_recovery.py
git commit -m "feat: HyperFlow restart recovery (plan_recovery + recover_runs)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 4: Local tools + `inspect` + `operator-inspect` flow

**Files:**
- Create: `backend/app/broski_operator/tools.py`
- Create: `backend/app/agents/hyperflow/flows/operator_inspect.yml`
- Modify: `backend/app/agents/hyperflow_runner.py` (`_do_node`, `_run` emit, new `_run_local_tool`, import)
- Test: `backend/tests/test_operator_tools.py`

**Interfaces:**
- Consumes (Task 3): `FlowNode.idempotent`.
- Produces: `tools.LOCAL_TOOLS: dict[str, Callable[[dict], Awaitable[dict]]]` with key `"local.inspect"`.
- Produces: `async tools.inspect_stack(params: dict) -> dict` returning `{"ok": bool, "checked_at": iso, "attention": [str], "containers": {...}, "redis": {...}, "postgres": {...}, "queues": {...}, "disk": {...}, "models": {...}}`. `ok` is true only when `containers`, `redis` and `postgres` are all ok. Every section is `{"ok": bool, ...}`; a failing section carries `"error"`.
- Produces: runner behaviour — a `tool` node whose `tool` is in `LOCAL_TOOLS` runs in-process (still passes through `_safety_gate`), never calls the orchestrator, and its returned dict is stored in the node's completed history entry as `result["data"]`.
- Produces: flow `operator-inspect` (single node `inspect`, tool `local.inspect`, `idempotent: true`).
- Semantics note (documented, intentional): the run status is `completed` whenever the graph finishes; whether the stack is healthy is `report.ok` / the node's `success`.

- [ ] **Step 1: Write the failing tests** — `backend/tests/test_operator_tools.py`

```python
"""BROski operator — local tools, inspect, and runner integration."""

import asyncio

import httpx
import pytest

from app.agents.hyperflow.registry import get_flow
from app.agents.hyperflow.schema import FlowDefinition
from app.broski_operator import tools
from app.models.hyperflow import HyperFlowRunStatus
from tests.test_hyperflow import _runner_with_io


@pytest.fixture(autouse=True)
def _safety_off(monkeypatch):
    monkeypatch.setenv("SAFETY_SHEPHERD_MODE", "off")


def _patch_sections(monkeypatch, **overrides):
    async def _ok():
        return {"ok": True}

    for name in ("containers", "redis", "postgres", "queues", "disk", "models"):
        fn = overrides.get(name, _ok)
        monkeypatch.setattr(tools, f"_{name}_section" if name != "containers" else "_docker_section", fn)


def test_inspect_all_ok(monkeypatch):
    _patch_sections(monkeypatch)
    report = asyncio.run(tools.inspect_stack({}))
    assert report["ok"] is True
    assert report["attention"] == []
    assert set(report) >= {"containers", "redis", "postgres", "queues", "disk", "models", "checked_at"}


def test_inspect_fail_soft_when_postgres_down(monkeypatch):
    async def _boom():
        raise RuntimeError("connection refused")

    _patch_sections(monkeypatch, postgres=_boom)
    report = asyncio.run(tools.inspect_stack({}))
    assert report["ok"] is False
    assert report["postgres"]["ok"] is False
    assert "RuntimeError" in report["postgres"]["error"]
    assert any(a.startswith("postgres") for a in report["attention"])


def test_inspect_hung_section_times_out(monkeypatch):
    async def _hang():
        await asyncio.sleep(5)
        return {"ok": True}

    monkeypatch.setattr(tools, "SECTION_TIMEOUT_SECONDS", 0.05)
    _patch_sections(monkeypatch, containers=_hang)
    report = asyncio.run(tools.inspect_stack({}))
    assert report["containers"]["ok"] is False
    assert report["ok"] is False


def test_inspect_flags_unhealthy_containers_and_dlq(monkeypatch):
    async def _docker():
        return {"ok": True, "total": 3, "running": 2, "exited": [], "unhealthy": ["bad-one"]}

    async def _queues():
        return {"ok": True, "depths": {"hypercode-dlq": 4}}

    _patch_sections(monkeypatch, containers=_docker, queues=_queues)
    report = asyncio.run(tools.inspect_stack({}))
    assert report["ok"] is True  # informational, not a core failure
    assert any("unhealthy" in a and "bad-one" in a for a in report["attention"])
    assert any("dead-letter" in a for a in report["attention"])


def test_docker_section_summarises_containers(monkeypatch):
    payload = [
        {"Names": ["/hypercode-core"], "State": "running", "Status": "Up 2 hours (healthy)"},
        {"Names": ["/bad-one"], "State": "running", "Status": "Up 1 hour (unhealthy)"},
        {"Names": ["/old"], "State": "exited", "Status": "Exited (0) 3 days ago"},
    ]
    real = httpx.AsyncClient
    monkeypatch.setattr(
        tools.httpx,
        "AsyncClient",
        lambda **kw: real(
            transport=httpx.MockTransport(lambda req: httpx.Response(200, json=payload)), **kw
        ),
    )
    out = asyncio.run(tools._docker_section())
    assert out == {"ok": True, "total": 3, "running": 2, "exited": ["old"], "unhealthy": ["bad-one"]}


def test_local_tools_registry():
    assert "local.inspect" in tools.LOCAL_TOOLS


def _local_flow():
    return FlowDefinition.model_validate(
        {"name": "lt", "entry": "t", "nodes": [{"id": "t", "type": "tool", "tool": "local.fake"}]}
    )


def test_local_tool_node_bypasses_orchestrator_and_records_data(monkeypatch):
    runner, final = _runner_with_io(_local_flow(), "lt1", monkeypatch)

    async def _boom(node):
        raise AssertionError("orchestrator must not be called for a local tool")

    async def _fake(params):
        return {"ok": True, "n": 1}

    monkeypatch.setattr(runner, "_dispatch", _boom)
    monkeypatch.setitem(tools.LOCAL_TOOLS, "local.fake", _fake)
    asyncio.run(runner._run())
    assert final["status"] is HyperFlowRunStatus.COMPLETED
    done = [e for e in runner._history if e["status"] == "completed"][0]
    assert done["result"]["success"] is True
    assert done["result"]["data"] == {"ok": True, "n": 1}


def test_local_tool_not_ok_is_recorded_as_unsuccessful(monkeypatch):
    runner, final = _runner_with_io(_local_flow(), "lt2", monkeypatch)

    async def _red(params):
        return {"ok": False, "why": "red"}

    monkeypatch.setitem(tools.LOCAL_TOOLS, "local.fake", _red)
    asyncio.run(runner._run())
    done = [e for e in runner._history if e["status"] == "completed"][0]
    assert done["result"]["success"] is False
    assert done["result"]["data"]["why"] == "red"


def test_local_tool_exception_fails_the_run(monkeypatch):
    runner, final = _runner_with_io(_local_flow(), "lt3", monkeypatch)

    async def _raises(params):
        raise RuntimeError("boom")

    monkeypatch.setitem(tools.LOCAL_TOOLS, "local.fake", _raises)
    asyncio.run(runner._run())
    assert final["status"] is HyperFlowRunStatus.FAILED
    assert "boom" in final["error"]


def test_operator_inspect_flow_is_registered():
    fd = get_flow("operator-inspect")
    assert fd is not None and fd.intent
    node = fd.node("inspect")
    assert node.tool == "local.inspect" and node.idempotent is True
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_operator_tools.py -v -p no:cacheprovider`
Expected: FAIL (`ModuleNotFoundError: app.broski_operator.tools`).

- [ ] **Step 3: Create `backend/app/broski_operator/tools.py`**

```python
"""Local (in-core) tools that HyperFlow ``tool`` nodes can run without the orchestrator.

``inspect_stack`` is strictly read-only: Docker via the read-only socket proxy (GET only),
Redis PING, Postgres ``SELECT 1``, Celery queue depths (LLEN), disk usage, model list.
Each section is independent, time-limited and fail-soft.
"""

from __future__ import annotations

import asyncio
import shutil
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

import httpx
import redis.asyncio as aioredis
from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal

SECTION_TIMEOUT_SECONDS = 8.0
_QUEUES = ("hypercode-high", "hypercode-normal", "hypercode-low", "hypercode-dlq")
_MAX_NAMES = 50
_CORE_SECTIONS = ("containers", "redis", "postgres")


async def _docker_section() -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(
            f"{settings.DOCKER_SOCKET_PROXY_URL}/containers/json", params={"all": "true"}
        )
    resp.raise_for_status()
    rows = resp.json()

    def names(items: list[dict[str, Any]]) -> list[str]:
        return sorted((c.get("Names") or ["?"])[0].lstrip("/") for c in items)[:_MAX_NAMES]

    return {
        "ok": True,
        "total": len(rows),
        "running": sum(1 for c in rows if c.get("State") == "running"),
        "exited": names([c for c in rows if c.get("State") == "exited"]),
        "unhealthy": names([c for c in rows if "unhealthy" in (c.get("Status") or "")]),
    }


async def _redis_section() -> dict[str, Any]:
    r = aioredis.from_url(settings.HYPERCODE_REDIS_URL, decode_responses=True)
    try:
        await r.ping()
    finally:
        await r.aclose()
    return {"ok": True}


def _pg_ping() -> None:
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
    finally:
        db.close()


async def _postgres_section() -> dict[str, Any]:
    await asyncio.to_thread(_pg_ping)
    return {"ok": True}


async def _queues_section() -> dict[str, Any]:
    from app.core.celery_app import celery_app

    r = aioredis.from_url(celery_app.conf.broker_url, decode_responses=True)
    try:
        depths = {q: int(await r.llen(q)) for q in _QUEUES}
    finally:
        await r.aclose()
    return {"ok": True, "depths": depths}


async def _disk_section() -> dict[str, Any]:
    du = shutil.disk_usage("/")
    used_pct = round(100 * du.used / du.total, 1)
    return {"ok": used_pct < 90.0, "free_gb": round(du.free / 1e9, 1), "used_pct": used_pct}


async def _models_section() -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{settings.OLLAMA_HOST.rstrip('/')}/api/tags")
    resp.raise_for_status()
    return {"ok": True, "models": [m.get("name") for m in resp.json().get("models", [])][:10]}


async def _section(fn: Callable[[], Awaitable[dict[str, Any]]]) -> dict[str, Any]:
    try:
        return await asyncio.wait_for(fn(), timeout=SECTION_TIMEOUT_SECONDS)
    except Exception as exc:  # fail-soft by design: a broken dependency is a finding, not a crash
        return {"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:120]}"}


async def inspect_stack(params: dict[str, Any]) -> dict[str, Any]:
    """Read-only stack health report. Never raises."""
    fns = {
        "containers": _docker_section,
        "redis": _redis_section,
        "postgres": _postgres_section,
        "queues": _queues_section,
        "disk": _disk_section,
        "models": _models_section,
    }
    results = await asyncio.gather(*(_section(fn) for fn in fns.values()))
    report: dict[str, Any] = dict(zip(fns.keys(), results))

    attention: list[str] = []
    for name, section in report.items():
        if not section.get("ok"):
            attention.append(f"{name}: {section.get('error') or 'not ok'}")
    unhealthy = report["containers"].get("unhealthy") or []
    if unhealthy:
        attention.append(f"unhealthy containers: {', '.join(unhealthy)}")
    dlq = (report["queues"].get("depths") or {}).get("hypercode-dlq", 0)
    if dlq:
        attention.append(f"dead-letter queue has {dlq} tasks")

    return {
        "ok": all(report[k].get("ok") for k in _CORE_SECTIONS),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "attention": attention,
        **report,
    }


LOCAL_TOOLS: dict[str, Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]] = {
    "local.inspect": inspect_stack,
}
```

- [ ] **Step 4: Create the flow** — `backend/app/agents/hyperflow/flows/operator_inspect.yml`

```yaml
# BROski operator: read-only stack health inspection.
# Run it: POST /api/v1/operator/tasks {"tool": "hypercode.inspect", "arguments": {}}

name: operator-inspect
version: 1
entry: inspect
intent: "BROski operator read-only stack health inspection report of containers redis postgres queues disk and models"

nodes:
  - id: inspect
    type: tool
    tool: local.inspect
    idempotent: true

edges: []
```

- [ ] **Step 5: Wire local tools into the runner** — in `backend/app/agents/hyperflow_runner.py`:

5a. Add the import next to the other `app.` imports:

```python
from app.broski_operator.tools import LOCAL_TOOLS
```

5b. Replace `_do_node`:

```python
    async def _do_node(self, node: FlowNode) -> dict[str, Any]:
        if node.type is NodeType.HUMAN_APPROVAL_GATE:
            return await self._await_approval(node)
        # P0-2: consult Safety Shepherd before any agent/tool dispatch.
        await self._safety_gate(node)
        if node.type is NodeType.TOOL and node.tool in LOCAL_TOOLS:
            return await self._run_local_tool(node)
        return await self._dispatch(node)

    async def _run_local_tool(self, node: FlowNode) -> dict[str, Any]:
        """Run an in-core tool. No orchestrator hop and no mocked-OK fallback."""
        data = await LOCAL_TOOLS[node.tool](node.params)
        ok = bool(data.get("ok"))
        return {"ok": ok, "green": ok, "data": data}
```

5c. In `_run`, record the tool data in the completed entry — after the existing `if result.get("mocked"):` block, add:

```python
                if "data" in result:
                    emit_result["data"] = result["data"]
```

- [ ] **Step 6: Run to verify pass, and re-check the flow-matching tests**

Run: `cd backend && python -m pytest tests/test_operator_tools.py tests/test_hyperflow.py tests/test_goal_matcher.py tests/test_flows_endpoint.py -v -p no:cacheprovider`
Expected: all PASS. If a goal-matcher test now fails because `operator-inspect`'s intent steals a match, reword only the `intent:` string in `operator_inspect.yml` to use more operator-specific words (keep it non-empty; `test_all_registered_flows_declare_intent` requires that) and re-run.

- [ ] **Step 7: Commit**

```bash
git add backend/app/broski_operator/tools.py backend/app/agents/hyperflow/flows/operator_inspect.yml backend/app/agents/hyperflow_runner.py backend/tests/test_operator_tools.py
git commit -m "feat: local tools + read-only inspect + operator-inspect flow

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 5: Operator API (`/api/v1/operator/tasks`)

**Files:**
- Create: `backend/app/broski_operator/status.py`, `backend/app/broski_operator/catalog.py`
- Create: `backend/app/api/v1/endpoints/operator_tasks.py`
- Modify: `backend/app/api/api.py` (mount)
- Test: `backend/tests/test_operator_api.py`

**Interfaces:**
- Consumes: `finish_run_row`, `store_decision` (Task 3, `runs.py`); `HyperFlowRunner.cancel`, `resume`; `get_runner`, `start_flow_run`; `get_flow`.
- Produces (`status.py`): `TERMINAL_RUN_STATUSES: frozenset[str]`; `to_task_status(run_status: str) -> str` (unknown → `"failed"`); `poll_interval_ms(task_status: str) -> Optional[int]` (`working`→2000, `input_required`→5000, else `None`); `progress_percent(total_nodes: int, history: list[dict], run_status: str) -> int`; `build_result(history: list[dict]) -> dict` → `{"success": bool|None, "report": dict|None, "nodes": [str]}`.
- Produces (`catalog.py`): `TOOL_FLOWS = {"hypercode.inspect": "operator-inspect", "hypercode.smoke": "hyperflow-smoke"}`; `tool_for_flow(flow_name) -> Optional[str]`.
- Produces (`operator_tasks.py`): `router`; `operator_principal` dependency returning `{"kind": "agent"|"user", "name": str, "user_id": Optional[int]}`.
- Routes (mounted at `/api/v1/operator`):
  - `POST /tasks` `{"tool": str, "arguments": {}}` → `{"taskId","tool","status":"working","pollInterval":2000}`; 404 `{"error":"unknown_tool","tools":[...]}`; 422 on bad body or non-empty `arguments`.
  - `GET /tasks/{id}` → `{"taskId","tool","status","progress","pollInterval","updatedAt","result","error","inputRequests"}`; 404 unknown. `result` only when `completed`, `error` only when `failed`/`cancelled`, `inputRequests` only when `input_required`.
  - `POST /tasks/{id}/input` `{"decision":"approve"|"reject"}` → `{"taskId","accepted":true,"decision"}`; 403 for agent principals; 422 bad decision; 404; 409 `not_awaiting_input` / `decision_already_pending`.
  - `POST /tasks/{id}/cancel` `{"reason"?: str}` → `{"taskId","status","reason"}`; 404; 409 `already_terminal`.
- Auth: `X-Agent-Key` (agent) or Bearer JWT (user); neither → 401.

- [ ] **Step 1: Write the failing tests** — `backend/tests/test_operator_api.py`

```python
"""BROski operator — status mapping + /api/v1/operator routes."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api.v1.endpoints import operator_tasks
from app.broski_operator import status
from app.main import app
from app.models.hyperflow import HyperFlowRun

BASE = "/api/v1/operator"


# ── pure mapping ─────────────────────────────────────────────────────────────

def test_status_mapping():
    assert status.to_task_status("running") == "working"
    assert status.to_task_status("awaiting_approval") == "input_required"
    for s in ("completed", "failed", "cancelled"):
        assert status.to_task_status(s) == s
    assert status.to_task_status("weird") == "failed"  # never leave a client polling forever


def test_poll_interval():
    assert status.poll_interval_ms("working") == 2000
    assert status.poll_interval_ms("input_required") == 5000
    assert status.poll_interval_ms("completed") is None


def test_progress_percent():
    hist = [{"node": "a", "status": "completed"}, {"node": "a", "status": "completed"}]
    assert status.progress_percent(2, hist, "running") == 50
    assert status.progress_percent(2, [], "running") == 0
    assert status.progress_percent(2, hist, "completed") == 100
    assert status.progress_percent(0, [], "running") == 0
    full = [{"node": "a", "status": "completed"}, {"node": "b", "status": "completed"}]
    assert status.progress_percent(2, full, "running") == 99  # only terminal state reaches 100


def test_build_result_uses_last_data_and_success():
    hist = [
        {"node": "i", "status": "completed", "result": {"success": False, "data": {"ok": False}}},
    ]
    assert status.build_result(hist) == {"success": False, "report": {"ok": False}, "nodes": ["i"]}
    assert status.build_result([]) == {"success": None, "report": None, "nodes": []}


# ── API ──────────────────────────────────────────────────────────────────────

def _as(kind="user", name="bro", user_id=1):
    app.dependency_overrides[operator_tasks.operator_principal] = lambda: {
        "kind": kind, "name": name, "user_id": user_id if kind == "user" else None,
    }


def _seed(db, run_id, run_status, history=None, flow="hyperflow-smoke", state_extra=None):
    state = {"history": history or []}
    state.update(state_extra or {})
    db.add(HyperFlowRun(id=run_id, flow_name=flow, flow_version=1, status=run_status,
                        current_node=None, state=state))
    db.commit()


class _FakeRunner:
    def __init__(self):
        self.resumed, self.cancelled = [], []

    def resume(self, approved):
        self.resumed.append(approved)

    async def cancel(self, reason):
        self.cancelled.append(reason)
        return True


def test_requires_authentication(client):
    assert client.post(f"{BASE}/tasks", json={"tool": "hypercode.inspect"}).status_code == 401
    assert client.get(f"{BASE}/tasks/x").status_code == 401


def test_start_unknown_tool_404(client):
    _as()
    r = client.post(f"{BASE}/tasks", json={"tool": "rm.rf", "arguments": {}})
    assert r.status_code == 404
    assert r.json()["detail"]["error"] == "unknown_tool"
    assert "hypercode.inspect" in r.json()["detail"]["tools"]


@pytest.mark.parametrize("body", [{}, {"tool": ""}, {"tool": 5}, {"tool": "hypercode.inspect", "arguments": []}])
def test_start_bad_body_422(client, body):
    _as()
    assert client.post(f"{BASE}/tasks", json=body).status_code == 422


def test_start_rejects_nonempty_arguments(client):
    _as()
    r = client.post(f"{BASE}/tasks", json={"tool": "hypercode.inspect", "arguments": {"x": 1}})
    assert r.status_code == 422  # Review focus 4: never silently ignored


def test_start_returns_handle_and_starts_flow(client, monkeypatch):
    _as()
    start = AsyncMock(return_value=None)
    monkeypatch.setattr(operator_tasks, "start_flow_run", start)
    r = client.post(f"{BASE}/tasks", json={"tool": "hypercode.inspect", "arguments": {}})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "working" and body["pollInterval"] == 2000
    assert body["tool"] == "hypercode.inspect" and body["taskId"]
    assert start.await_args.args[0].name == "operator-inspect"
    assert start.await_args.args[1] == body["taskId"]
    assert start.await_args.kwargs["user_id"] == 1


def test_agent_can_start_without_user_id(client, monkeypatch):
    _as(kind="agent", name="hypercode-mcp-server")
    start = AsyncMock(return_value=None)
    monkeypatch.setattr(operator_tasks, "start_flow_run", start)
    assert client.post(f"{BASE}/tasks", json={"tool": "hypercode.smoke"}).status_code == 200
    assert start.await_args.kwargs["user_id"] is None


def test_get_unknown_404(client):
    _as()
    assert client.get(f"{BASE}/tasks/nope").status_code == 404


def test_get_working_hides_result_and_error(client, db):
    _as()
    _seed(db, "w1", "running", [{"node": "ready", "status": "completed", "result": {"success": True}}])
    body = client.get(f"{BASE}/tasks/w1").json()
    assert body["status"] == "working" and body["progress"] == 50
    assert body["result"] is None and body["error"] is None and body["inputRequests"] is None
    assert body["pollInterval"] == 2000 and body["tool"] == "hypercode.smoke"


def test_get_completed_has_result(client, db):
    _as()
    hist = [{"node": "inspect", "status": "completed", "result": {"success": True, "data": {"ok": True}}}]
    _seed(db, "c1", "completed", hist, flow="operator-inspect")
    body = client.get(f"{BASE}/tasks/c1").json()
    assert body["status"] == "completed" and body["progress"] == 100
    assert body["result"] == {"success": True, "report": {"ok": True}, "nodes": ["inspect"]}
    assert body["error"] is None


def test_get_input_required_has_question(client, db):
    _as()
    hist = [{"node": "ready", "status": "awaiting_approval", "result": {"prompt": "Deploy it?"}}]
    _seed(db, "i1", "awaiting_approval", hist)
    body = client.get(f"{BASE}/tasks/i1").json()
    assert body["status"] == "input_required"
    assert body["inputRequests"]["approval"]["question"] == "Deploy it?"
    assert body["inputRequests"]["approval"]["options"] == ["approve", "reject"]


def test_get_failed_and_cancelled_expose_error(client, db):
    _as()
    _seed(db, "f1", "failed", state_extra={"error": "boom"})
    _seed(db, "x1", "cancelled", state_extra={"error": "stop"})
    assert client.get(f"{BASE}/tasks/f1").json()["error"] == "boom"
    assert client.get(f"{BASE}/tasks/x1").json()["error"] == "stop"


def test_input_forbidden_for_agent_keys(client, db):
    _as(kind="agent", name="hypercode-mcp-server")
    _seed(db, "a1", "awaiting_approval")
    r = client.post(f"{BASE}/tasks/a1/input", json={"decision": "approve"})
    assert r.status_code == 403  # Review focus 3


def test_input_validation_and_state_checks(client, db):
    _as()
    _seed(db, "v1", "running")
    assert client.post(f"{BASE}/tasks/v1/input", json={"decision": "maybe"}).status_code == 422
    assert client.post(f"{BASE}/tasks/nope/input", json={"decision": "approve"}).status_code == 404
    r = client.post(f"{BASE}/tasks/v1/input", json={"decision": "approve"})
    assert r.status_code == 409 and r.json()["detail"]["error"] == "not_awaiting_input"


def test_input_stores_decision_signals_runner_and_refuses_duplicate(client, db, monkeypatch):
    _as()
    _seed(db, "ok1", "awaiting_approval")
    fake = _FakeRunner()
    monkeypatch.setattr(operator_tasks, "get_runner", lambda run_id: fake)
    r = client.post(f"{BASE}/tasks/ok1/input", json={"decision": "approve"})
    assert r.status_code == 200 and r.json()["accepted"] is True
    assert fake.resumed == [True]
    db.expire_all()
    run = db.get(HyperFlowRun, "ok1")
    assert run.state["context"]["pending_decision"]["approved"] is True
    dup = client.post(f"{BASE}/tasks/ok1/input", json={"decision": "reject"})
    assert dup.status_code == 409 and dup.json()["detail"]["error"] == "decision_already_pending"


def test_input_without_live_runner_still_persists(client, db, monkeypatch):
    _as()
    _seed(db, "ok2", "awaiting_approval")
    monkeypatch.setattr(operator_tasks, "get_runner", lambda run_id: None)
    assert client.post(f"{BASE}/tasks/ok2/input", json={"decision": "reject"}).status_code == 200
    db.expire_all()
    assert db.get(HyperFlowRun, "ok2").state["context"]["pending_decision"]["approved"] is False


def test_cancel_unknown_and_terminal(client, db):
    _as()
    assert client.post(f"{BASE}/tasks/nope/cancel", json={}).status_code == 404
    _seed(db, "t1", "completed")
    r = client.post(f"{BASE}/tasks/t1/cancel", json={})
    assert r.status_code == 409 and r.json()["detail"]["error"] == "already_terminal"


def test_cancel_without_live_runner_marks_row(client, db, monkeypatch):
    _as()
    _seed(db, "k1", "awaiting_approval")
    monkeypatch.setattr(operator_tasks, "get_runner", lambda run_id: None)
    r = client.post(f"{BASE}/tasks/k1/cancel", json={"reason": "no longer needed"})
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled" and "no longer needed" in r.json()["reason"]
    db.expire_all()
    run = db.get(HyperFlowRun, "k1")
    assert run.status == "cancelled" and run.completed_at is not None


def test_cancel_live_runner_is_asked_to_cancel(client, db, monkeypatch):
    _as()
    _seed(db, "k2", "running")
    fake = _FakeRunner()
    monkeypatch.setattr(operator_tasks, "get_runner", lambda run_id: fake)
    assert client.post(f"{BASE}/tasks/k2/cancel", json={"reason": "abort"}).status_code == 200
    assert len(fake.cancelled) == 1 and "abort" in fake.cancelled[0]


def test_cancel_reason_must_be_short_string(client, db):
    _as()
    _seed(db, "k3", "running")
    assert client.post(f"{BASE}/tasks/k3/cancel", json={"reason": 5}).status_code == 422
    assert client.post(f"{BASE}/tasks/k3/cancel", json={"reason": "x" * 201}).status_code == 422
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_operator_api.py -v -p no:cacheprovider`
Expected: FAIL (`ModuleNotFoundError: app.api.v1.endpoints.operator_tasks`).

- [ ] **Step 3: Create `backend/app/broski_operator/status.py`**

```python
"""Pure mapping between HyperFlow run state and MCP-Tasks-shaped task state."""

from __future__ import annotations

from typing import Any, Optional

TERMINAL_RUN_STATUSES = frozenset({"completed", "failed", "cancelled"})

_STATUS_MAP = {
    "running": "working",
    "awaiting_approval": "input_required",
    "completed": "completed",
    "failed": "failed",
    "cancelled": "cancelled",
}
_POLL_MS = {"working": 2000, "input_required": 5000}


def to_task_status(run_status: str) -> str:
    """Map a HyperFlow run status to a task status. Unknown → 'failed' (never poll forever)."""
    return _STATUS_MAP.get(run_status, "failed")


def poll_interval_ms(task_status: str) -> Optional[int]:
    return _POLL_MS.get(task_status)


def progress_percent(total_nodes: int, history: list[dict[str, Any]], run_status: str) -> int:
    """Share of distinct nodes completed. Only a completed run reports 100."""
    if run_status == "completed":
        return 100
    if total_nodes <= 0:
        return 0
    done = {e["node"] for e in history if e.get("status") == "completed" and e.get("node")}
    return min(99, int(100 * len(done) / total_nodes))


def build_result(history: list[dict[str, Any]]) -> dict[str, Any]:
    """Final result: last node success, last tool report, ordered completed node ids."""
    success: Optional[bool] = None
    report: Optional[dict[str, Any]] = None
    nodes: list[str] = []
    for entry in history:
        if entry.get("status") != "completed" or not entry.get("node"):
            continue
        result = entry.get("result") or {}
        nodes.append(entry["node"])
        success = bool(result.get("success", True))
        if "data" in result:
            report = result["data"]
    return {"success": success, "report": report, "nodes": nodes}
```

- [ ] **Step 4: Create `backend/app/broski_operator/catalog.py`**

```python
"""Allow-list of operator tools → HyperFlow flow names. Anything not listed cannot be started."""

from __future__ import annotations

from typing import Optional

TOOL_FLOWS: dict[str, str] = {
    "hypercode.inspect": "operator-inspect",
    # Deterministic two-gate demo flow; used to prove approvals survive a restart.
    "hypercode.smoke": "hyperflow-smoke",
}


def tool_for_flow(flow_name: str) -> Optional[str]:
    for tool, flow in TOOL_FLOWS.items():
        if flow == flow_name:
            return tool
    return None
```

- [ ] **Step 5: Create `backend/app/api/v1/endpoints/operator_tasks.py`**

```python
"""BROski operator API — MCP-Tasks-shaped facade over HyperFlow runs (spec 2026-09-26).

Routes (mounted under ``/api/v1/operator``):
    POST /tasks               — start an allow-listed tool, returns a task handle at once
    GET  /tasks/{id}          — poll status / progress / result
    POST /tasks/{id}/input    — approve or reject a parked approval gate (humans only)
    POST /tasks/{id}/cancel   — cancel a task

Auth: ``X-Agent-Key`` (agents) or a Bearer JWT (humans). Agents can start, read and cancel
tasks but can NEVER submit an approval: the model must not approve its own risky action.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.hyperflow.registry import get_flow
from app.agents.hyperflow_runner import get_runner, start_flow_run
from app.api import deps
from app.broski_operator.catalog import TOOL_FLOWS, tool_for_flow
from app.broski_operator.runs import finish_run_row, store_decision
from app.broski_operator.status import (
    TERMINAL_RUN_STATUSES,
    build_result,
    poll_interval_ms,
    progress_percent,
    to_task_status,
)
from app.db.session import get_db
from app.middleware.agent_auth import get_agent_from_key
from app.models.hyperflow import HyperFlowRun, HyperFlowRunStatus

router = APIRouter()

_MAX_REASON = 200


async def operator_principal(
    agent: Optional[dict] = Depends(get_agent_from_key),
    user: Any = Depends(deps.get_optional_current_user),
) -> dict[str, Any]:
    """Agent key or human JWT. Neither → 401."""
    if agent is not None:
        return {"kind": "agent", "name": agent["agent_name"], "user_id": None}
    if user is not None:
        if not getattr(user, "is_active", True):
            raise HTTPException(status_code=403, detail="Inactive user")
        return {"kind": "user", "name": getattr(user, "email", "user"), "user_id": user.id}
    raise HTTPException(
        status_code=401, detail="Authentication required (Bearer token or X-Agent-Key)"
    )


def _approval_request(history: list[dict[str, Any]]) -> dict[str, Any]:
    for entry in reversed(history):
        if entry.get("status") == "awaiting_approval":
            prompt = (entry.get("result") or {}).get("prompt", "Approve?")
            return {
                "approval": {
                    "node": entry.get("node"),
                    "question": prompt,
                    "options": ["approve", "reject"],
                }
            }
    return {"approval": {"question": "Approve?", "options": ["approve", "reject"]}}


def _serialize(run: HyperFlowRun) -> dict[str, Any]:
    state = run.state or {}
    history = state.get("history", [])
    flow = get_flow(run.flow_name)
    task_status = to_task_status(run.status)
    when = run.updated_at or run.created_at
    body: dict[str, Any] = {
        "taskId": run.id,
        "tool": tool_for_flow(run.flow_name),
        "status": task_status,
        "progress": progress_percent(len(flow.nodes) if flow else 0, history, run.status),
        "pollInterval": poll_interval_ms(task_status),
        "updatedAt": when.isoformat() if when else None,
        "result": None,
        "error": None,
        "inputRequests": None,
    }
    if task_status == "completed":
        body["result"] = build_result(history)
    elif task_status in ("failed", "cancelled"):
        body["error"] = state.get("error")
    elif task_status == "input_required":
        body["inputRequests"] = _approval_request(history)
    return body


def _get_run(db: Session, task_id: str) -> HyperFlowRun:
    run = db.get(HyperFlowRun, task_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return run


@router.post("/tasks")
async def start_task(
    payload: dict,
    principal: dict = Depends(operator_principal),
) -> Any:
    tool = payload.get("tool")
    arguments = payload.get("arguments", {})
    if not isinstance(tool, str) or not tool:
        raise HTTPException(status_code=422, detail="'tool' must be a non-empty string")
    if not isinstance(arguments, dict):
        raise HTTPException(status_code=422, detail="'arguments' must be an object")
    if arguments:
        raise HTTPException(status_code=422, detail="This tool does not accept arguments yet")
    flow_name = TOOL_FLOWS.get(tool)
    if flow_name is None:
        raise HTTPException(
            status_code=404, detail={"error": "unknown_tool", "tools": sorted(TOOL_FLOWS)}
        )
    flow = get_flow(flow_name)
    if flow is None:
        raise HTTPException(status_code=500, detail=f"Flow '{flow_name}' is not installed")
    run_id = str(uuid.uuid4())
    await start_flow_run(flow, run_id, user_id=principal["user_id"])
    return {
        "taskId": run_id,
        "tool": tool,
        "status": "working",
        "pollInterval": poll_interval_ms("working"),
    }


@router.get("/tasks/{task_id}")
def get_task(
    task_id: str,
    db: Session = Depends(get_db),
    _principal: dict = Depends(operator_principal),
) -> Any:
    return _serialize(_get_run(db, task_id))


@router.post("/tasks/{task_id}/input")
async def submit_input(
    task_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    principal: dict = Depends(operator_principal),
) -> Any:
    if principal["kind"] != "user":
        raise HTTPException(
            status_code=403,
            detail="Approvals require an authenticated human user, not an agent key",
        )
    decision = payload.get("decision")
    if decision not in ("approve", "reject"):
        raise HTTPException(status_code=422, detail="'decision' must be 'approve' or 'reject'")
    run = _get_run(db, task_id)
    if run.status != HyperFlowRunStatus.AWAITING_APPROVAL.value:
        raise HTTPException(
            status_code=409,
            detail={"error": "not_awaiting_input", "status": to_task_status(run.status)},
        )
    approved = decision == "approve"
    if not store_decision(db, run, approved=approved, by=principal["name"]):
        raise HTTPException(status_code=409, detail={"error": "decision_already_pending"})
    runner = get_runner(task_id)
    if runner is not None:
        runner.resume(approved)
    return {"taskId": task_id, "accepted": True, "decision": decision}


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(
    task_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    principal: dict = Depends(operator_principal),
) -> Any:
    reason = payload.get("reason") or "cancelled by operator"
    if not isinstance(reason, str) or len(reason) > _MAX_REASON:
        raise HTTPException(status_code=422, detail=f"'reason' must be a string <= {_MAX_REASON} chars")
    run = _get_run(db, task_id)
    if run.status in TERMINAL_RUN_STATUSES:
        raise HTTPException(
            status_code=409,
            detail={"error": "already_terminal", "status": to_task_status(run.status)},
        )
    label = f"{reason} (by {principal['name']})"
    runner = get_runner(task_id)
    if runner is None or not await runner.cancel(label):
        finish_run_row(db, run, HyperFlowRunStatus.CANCELLED, label)
    db.refresh(run)
    return {"taskId": task_id, "status": to_task_status(run.status), "reason": label}
```

- [ ] **Step 6: Mount the router** — in `backend/app/api/api.py`, insert directly above the line `api_router.include_router(health.router,   prefix="",           tags=["health"])` (use the file's existing try/except-import style):

```python
try:
    from app.api.v1.endpoints import operator_tasks
    api_router.include_router(operator_tasks.router, prefix="/operator", tags=["operator"])  # BROski operator tasks
except Exception as _e:
    import logging as _log
    _log.getLogger(__name__).warning("Operator endpoints unavailable: %s", _e)
```

- [ ] **Step 7: Run to verify pass**

Run: `cd backend && python -m pytest tests/test_operator_api.py -v -p no:cacheprovider`
Expected: all PASS. (`test_requires_authentication` relies on `get_optional_current_user` returning `None` with no token; if it returns 401/403 differently, adjust only that test's expected code after reading `deps.py`.)

- [ ] **Step 8: Regression run of everything touched so far**

Run: `cd backend && python -m pytest tests/test_operator_api.py tests/test_operator_tools.py tests/test_operator_recovery.py tests/test_operator_durable_approval.py tests/test_operator_runner.py tests/test_hyperflow.py tests/test_flows_endpoint.py tests/test_goal_matcher.py -q -p no:cacheprovider`
Expected: all PASS.

- [ ] **Step 9: Commit**

```bash
git add backend/app/broski_operator/status.py backend/app/broski_operator/catalog.py backend/app/api/v1/endpoints/operator_tasks.py backend/app/api/api.py backend/tests/test_operator_api.py
git commit -m "feat: BROski operator API (/api/v1/operator/tasks)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 6: MCP tools on `hypercode-mcp-server`

**Files:**
- Modify: `services/hypercode-mcp-server/server.py`
- Modify: `docker-compose.agents.yml` (service `hypercode-mcp-server` environment)
- Test: `backend/tests/test_operator_mcp_tools.py`

**Interfaces:**
- Consumes: the four routes from Task 5 (`POST /api/v1/operator/tasks`, `GET …/tasks/{id}`, `POST …/tasks/{id}/cancel`).
- Produces (MCP tools): `hypercode_inspect() -> dict`, `hypercode_task_get(task_id: str) -> dict`, `hypercode_task_cancel(task_id: str, reason: str = "") -> dict`. **No approval tool** (deliberate: approvals are human-only, see Task 7 amendments).
- Produces: `_core_headers(base: str) -> dict` — `{"X-Agent-Key": <env HYPERCODE_AGENT_KEY>}` only when the key is set and `base == CORE_URL`, else `{}`.

- [ ] **Step 1: Probe the MCP SDK for native Tasks support (informational, no code change)**

Run: `docker exec hypercode-mcp-server python -c "import importlib.metadata as m, mcp.types as t; print(m.version('mcp'), sorted(n for n in dir(t) if 'Task' in n)[:20])"`
Expected: prints the SDK version and any `Task*` names. Record the output line for Task 7's spec amendment. Either result leads to the same build (ordinary tools with Tasks-shaped payloads); native Tasks is a later swap. If the container isn't running, skip and write "probe skipped: container down" in the amendment.

- [ ] **Step 2: Write the failing tests** — `backend/tests/test_operator_mcp_tools.py`

```python
"""BROski operator — MCP tools on hypercode-mcp-server (loaded from its source file)."""

import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

SERVER = Path(__file__).resolve().parents[2] / "services" / "hypercode-mcp-server" / "server.py"
pytestmark = pytest.mark.skipif(not SERVER.exists(), reason="services/ not present in this image")

GOOD_ID = "0f8fad5b-d9cb-469f-a165-70867728950e"


def _load(monkeypatch, key=""):
    monkeypatch.setenv("HYPERCODE_AGENT_KEY", key)
    spec = importlib.util.spec_from_file_location("hypercode_mcp_server_under_test", SERVER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_core_headers_only_for_core_and_only_with_key(monkeypatch):
    mod = _load(monkeypatch, key="k123")
    assert mod._core_headers(mod.CORE_URL) == {"X-Agent-Key": "k123"}
    assert mod._core_headers(mod.ORCH_URL) == {}  # never leaked to other hosts
    assert _load(monkeypatch, key="")._core_headers(mod.CORE_URL) == {}


def test_inspect_posts_the_allow_listed_tool(monkeypatch):
    import asyncio

    mod = _load(monkeypatch)
    mod._post = AsyncMock(return_value={"taskId": GOOD_ID})
    out = asyncio.run(mod.hypercode_inspect())
    assert out == {"taskId": GOOD_ID}
    mod._post.assert_awaited_once_with(
        "/api/v1/operator/tasks", {"tool": "hypercode.inspect", "arguments": {}}
    )


def test_task_get_and_cancel_hit_the_right_routes(monkeypatch):
    import asyncio

    mod = _load(monkeypatch)
    mod._get = AsyncMock(return_value={"status": "working"})
    mod._post = AsyncMock(return_value={"status": "cancelled"})
    assert asyncio.run(mod.hypercode_task_get(GOOD_ID)) == {"status": "working"}
    mod._get.assert_awaited_once_with(f"/api/v1/operator/tasks/{GOOD_ID}")
    assert asyncio.run(mod.hypercode_task_cancel(GOOD_ID, "done with it")) == {"status": "cancelled"}
    mod._post.assert_awaited_once_with(
        f"/api/v1/operator/tasks/{GOOD_ID}/cancel", {"reason": "done with it"}
    )


@pytest.mark.parametrize("bad", ["../../admin", "x/../y", "", "a b", GOOD_ID + "/cancel"])
def test_bad_task_ids_rejected_before_any_http_call(monkeypatch, bad):
    import asyncio

    mod = _load(monkeypatch)
    mod._get = AsyncMock()
    mod._post = AsyncMock()
    assert "error" in asyncio.run(mod.hypercode_task_get(bad))
    assert "error" in asyncio.run(mod.hypercode_task_cancel(bad, ""))
    mod._get.assert_not_awaited()
    mod._post.assert_not_awaited()
```

These tests use `asyncio.run` and do not depend on pytest-asyncio.

- [ ] **Step 3: Run to verify failure**

Run: `cd backend && python -m pytest tests/test_operator_mcp_tools.py -v -p no:cacheprovider`
Expected: FAIL (`AttributeError: ... _core_headers`).

- [ ] **Step 4: Implement in `services/hypercode-mcp-server/server.py`**

4a. Add `import re` next to `import os`, and after the `TIMEOUT = 10.0` line add:

```python
# Agent key presented to hypercode-core's operator API (X-Agent-Key). Optional: without it
# operator calls return 401. Never logged; only ever sent to CORE_URL.
AGENT_KEY   = os.getenv("HYPERCODE_AGENT_KEY", "")
_TASK_ID_RE = re.compile(r"^[0-9a-fA-F-]{36}$")
```

4b. Replace the two HTTP helpers:

```python
def _core_headers(base: str) -> dict:
    """X-Agent-Key for calls to hypercode-core only — never sent to any other host."""
    return {"X-Agent-Key": AGENT_KEY} if AGENT_KEY and base == CORE_URL else {}


async def _get(path: str, base: str = CORE_URL, **params: Any) -> Any:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.get(f"{base}{path}", params=params or None, headers=_core_headers(base))
        r.raise_for_status()
        return r.json()


async def _post(path: str, body: dict, base: str = CORE_URL) -> Any:
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(f"{base}{path}", json=body, headers=_core_headers(base))
        r.raise_for_status()
        return r.json()
```

4c. Add the three tools directly above the `# ── Entry point` banner:

```python
# ── BROski operator tasks (async, durable) ────────────────────────────────────

@mcp.tool()
async def hypercode_inspect() -> dict:
    """
    Start a read-only stack health inspection as a background task.
    Returns a task handle immediately ({taskId, status:"working", pollInterval});
    poll it with hypercode_task_get. Never changes anything.
    """
    return await _post(
        f"{API_PREFIX}/operator/tasks", {"tool": "hypercode.inspect", "arguments": {}}
    )


@mcp.tool()
async def hypercode_task_get(task_id: str) -> dict:
    """
    Get a background task's status. status is one of working, input_required,
    completed, failed, cancelled. The result appears only when completed.
    input_required means a human must approve — approvals are not possible via this
    server by design.
    """
    if not _TASK_ID_RE.match(task_id or ""):
        return {"error": "invalid task_id"}
    return await _get(f"{API_PREFIX}/operator/tasks/{task_id}")


@mcp.tool()
async def hypercode_task_cancel(task_id: str, reason: str = "") -> dict:
    """Cancel a background task. Safe to call; already-finished tasks return a 409 error."""
    if not _TASK_ID_RE.match(task_id or ""):
        return {"error": "invalid task_id"}
    return await _post(
        f"{API_PREFIX}/operator/tasks/{task_id}/cancel", {"reason": reason[:200]}
    )
```

4d. Update the module docstring's tool list by appending these three lines after `hypercode_execute_agent`:

```
  hypercode_inspect         — start a read-only stack inspection (background task)
  hypercode_task_get        — poll a background task
  hypercode_task_cancel     — cancel a background task
```

- [ ] **Step 5: Add the env var to compose** — in `docker-compose.agents.yml`, service `hypercode-mcp-server`, `environment:` list, add after `HYPERCODE_ORCH_URL`:

```yaml
      - HYPERCODE_AGENT_KEY=${HYPERCODE_AGENT_KEY:-}
```

- [ ] **Step 6: Run to verify pass**

Run: `cd backend && python -m pytest tests/test_operator_mcp_tools.py -v -p no:cacheprovider`
Expected: PASS (or all SKIPPED if `services/` is absent; on the host it is present).

- [ ] **Step 7: Commit**

```bash
git add services/hypercode-mcp-server/server.py docker-compose.agents.yml backend/tests/test_operator_mcp_tools.py
git commit -m "feat: MCP tools for BROski operator tasks (inspect/get/cancel)

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

---

### Task 7: Live proof, deploy, docs

**Files:**
- Create: `scripts/prove-operator.py`
- Modify: `docs/superpowers/specs/2026-09-26-broski-operator-design.md` (append amendments)
- Modify: `WHATS_DONE.md` (new top entry)

**Interfaces:**
- Consumes: everything above. Runs inside the `hypercode-core` container so no token ever leaves it.
- Produces: `scripts/prove-operator.py <phase1|phase2 TASK_ID>`. Prints only task ids and PASS/FAIL lines. Exit code non-zero on any failed assertion.

- [ ] **Step 1: Create `scripts/prove-operator.py`**

```python
"""Live proof for the BROski operator. Runs INSIDE hypercode-core so tokens never leave it:

    docker exec -i hypercode-core python - phase1 < scripts/prove-operator.py
    docker restart hypercode-core        # (after phase1 prints PARKED_TASK=<id>)
    docker exec -i hypercode-core python - phase2 <id> < scripts/prove-operator.py

phase1: inspect -> completed report; cancel proof; then parks a two-gate task at input_required.
phase2: (after the restart) the parked task resumes at its gate, is approved twice, completes.
Prints only ids and PASS/FAIL lines. Never prints the token.
"""

import sys
import time

import httpx

from app.core.security import create_access_token
from app.db.session import SessionLocal
from app.models.models import User

BASE = "http://localhost:8000/api/v1/operator"


def _token() -> str:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.is_superuser.is_(True), User.is_active.is_(True)).first()
        if user is None:
            sys.exit("FAIL: no active superuser to mint a proof token for")
        return create_access_token(subject=user.id)
    finally:
        db.close()


HEADERS = {"Authorization": f"Bearer {_token()}"}


def call(method: str, path: str, **kw):
    r = httpx.request(method, BASE + path, headers=HEADERS, timeout=30, **kw)
    return r.status_code, r.json()


def wait_for(task_id: str, want: set, timeout: int = 120) -> dict:
    end, last = time.time() + timeout, None
    while time.time() < end:
        try:
            code, body = call("GET", f"/tasks/{task_id}")
            last = body.get("status")
            if code == 200 and last in want:
                return body
        except httpx.HTTPError:
            pass  # core may still be restarting
        time.sleep(2)
    sys.exit(f"FAIL: timed out waiting for {sorted(want)} on {task_id}; last status={last}")


def check(ok: bool, label: str) -> None:
    print(("PASS: " if ok else "FAIL: ") + label)
    if not ok:
        sys.exit(1)


def phase1() -> None:
    code, h = call("POST", "/tasks", json={"tool": "hypercode.inspect", "arguments": {}})
    check(code == 200 and h["status"] == "working" and h["taskId"], "inspect returns a handle immediately")
    done = wait_for(h["taskId"], {"completed", "failed"})
    check(done["status"] == "completed", "inspect completed after we 'disconnected' and polled later")
    report = done["result"]["report"]
    print(f"INFO: stack ok={report['ok']} attention={report['attention']}")
    check(all(k in report for k in ("containers", "redis", "postgres", "queues", "disk")), "report has all sections")

    code, c = call("POST", "/tasks", json={"tool": "hypercode.smoke", "arguments": {}})
    wait_for(c["taskId"], {"input_required"})
    code, cancelled = call("POST", f"/tasks/{c['taskId']}/cancel", json={"reason": "proof cancel"})
    check(code == 200 and cancelled["status"] == "cancelled", "cancel mid-flight -> cancelled")
    time.sleep(3)
    _, after = call("GET", f"/tasks/{c['taskId']}")
    check(after["status"] == "cancelled", "cancelled task stays cancelled (no further transitions)")

    code, p = call("POST", "/tasks", json={"tool": "hypercode.smoke", "arguments": {}})
    parked = wait_for(p["taskId"], {"input_required"})
    check(parked["inputRequests"]["approval"]["question"], "run parked at an approval gate")
    print(f"PARKED_TASK={p['taskId']}")


def phase2(task_id: str) -> None:
    wait_for(task_id, {"input_required"})
    print("INFO: parked task is visible again after the restart")
    for gate in (1, 2):
        code, body = call("POST", f"/tasks/{task_id}/input", json={"decision": "approve"})
        check(code == 200 and body["accepted"], f"approval {gate} accepted after restart")
        if gate == 1:
            # Wait for the run to reach the SECOND gate (not the still-visible first one).
            end = time.time() + 120
            while time.time() < end:
                _, b = call("GET", f"/tasks/{task_id}")
                if b["status"] == "input_required" and b["inputRequests"]["approval"]["node"] == "finish":
                    break
                time.sleep(2)
            else:
                sys.exit("FAIL: second gate never appeared")
    done = wait_for(task_id, {"completed", "failed"})
    check(done["status"] == "completed", "task completed after approvals that survived a core restart")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "phase1":
        phase1()
    elif len(sys.argv) >= 3 and sys.argv[1] == "phase2":
        phase2(sys.argv[2])
    else:
        sys.exit("usage: phase1 | phase2 <task_id>")
```

- [ ] **Step 2: Syntax-check the script locally**

Run: `python -c "import ast,sys; ast.parse(open('scripts/prove-operator.py', encoding='utf-8').read()); print('syntax ok')"`
Expected: `syntax ok`.

- [ ] **Step 3: RAM gate (do not skip)**

Run: `wsl -e free -m`
Expected: `available` ≥ 1200 MB. If lower, STOP and ask Bro to stop the observability stack (or trim idle agents) first — do not do it silently; the box wedges below ~0.5 GB (WHATS_DONE N22, memory `hyperfocuszone-8gb-ram-ceiling`).

- [ ] **Step 4: Full new-test regression on the host before building**

Run: `cd backend && python -m pytest tests/test_operator_api.py tests/test_operator_tools.py tests/test_operator_recovery.py tests/test_operator_durable_approval.py tests/test_operator_runner.py tests/test_operator_mcp_tools.py tests/test_hyperflow.py tests/test_flows_endpoint.py tests/test_goal_matcher.py -q -p no:cacheprovider`
Expected: all PASS.

- [ ] **Step 5: Build the two changed images**

Run (repo root, background — it can take many minutes under RAM pressure; watch `wsl -e free -m` and do nothing else heavy):
`docker compose -f docker-compose.yml -f docker-compose.agents.yml build hypercode-core hypercode-mcp-server`
Expected: both images build, exit 0.

- [ ] **Step 6: Recreate only those two services**

Run: `docker compose -f docker-compose.yml -f docker-compose.agents.yml up -d --no-deps hypercode-core hypercode-mcp-server`
Then wait for health: `docker inspect -f "{{.State.Health.Status}}" hypercode-core` → `healthy` (repeat until so). Then `docker logs hypercode-core --tail 30` and confirm a `HyperFlow recovery:` line. Do NOT use `--force-recreate`, `--remove-orphans`, or `docker compose config`.

- [ ] **Step 7: Live proof, phase 1**

Run: `docker exec -i hypercode-core python - phase1 < scripts/prove-operator.py`
Expected: every line `PASS:`, ending with `PARKED_TASK=<uuid>`. Any `FAIL:` → stop, use superpowers:systematic-debugging, fix, re-run; do not claim success.

- [ ] **Step 8: Restart core, live proof phase 2**

Run: `docker restart hypercode-core`, wait until `healthy`, then
`docker exec -i hypercode-core python - phase2 <the PARKED_TASK uuid> < scripts/prove-operator.py`
Expected: `PASS` for "parked task is visible", both approvals, and "task completed after approvals that survived a core restart". Also `docker logs hypercode-core --tail 50` should show a `hyperflow recovery run=<uuid> action=resume` line.

- [ ] **Step 9: MCP live check (only if `HYPERCODE_AGENT_KEY` is provisioned)**

Provisioning a key is Bro's step (superuser `POST /api/v1/agent-keys`, see `backend/app/api/v1/endpoints/agent_keys.py`; the raw key is shown once and must go straight into `.env` as `HYPERCODE_AGENT_KEY` without passing through chat or logs). If it is not set, record "MCP live check: pending key provisioning" in WHATS_DONE and do NOT fake it. If set: recreate `hypercode-mcp-server` (same `up -d --no-deps`), then call `hypercode_inspect` then `hypercode_task_get` from an MCP client and confirm a completed report.

- [ ] **Step 10: Append the spec amendments** to `docs/superpowers/specs/2026-09-26-broski-operator-design.md`:

```markdown

## 9. Amendments made while planning (2026-09-26)

- **Approvals are human-only.** `POST /tasks/{id}/input` requires a Bearer JWT; an `X-Agent-Key` gets 403. The MCP server holds only an agent key, so it exposes **no approval tool** (§5.4's `task_update` is dropped): the model must not approve its own risky action. Approvals happen in the dashboard / authenticated API.
- **`arguments` must be `{}`** in Phase 1 (inspect takes none); non-empty is a 422, never silently ignored.
- **Recovery rule for a step in flight at crash time:** re-run only if the node is `idempotent: true` or is an approval gate; otherwise fail the run with `interrupted by restart`. Loop counters and the originating `user_id` are not restored.
- **Run status vs health:** a run is `completed` when the graph finishes; whether the stack is healthy is `result.report.ok` / `result.success`.
- **DB-only cancel** (run not live in this process) goes through the same terminal-entry helper; no separate Redis publish.
- **MCP Tasks extension probe result:** <paste the Step 1 output line from Task 6, or "probe skipped: container down">. Ordinary tools with Tasks-shaped payloads ship either way.
- **Pending decision race guard:** a second decision while one is pending is a 409 `decision_already_pending`.
```

Replace the `<paste …>` placeholder with the real probe output before committing.

- [ ] **Step 11: Add the WHATS_DONE entry** — in `WHATS_DONE.md`, insert directly under the `> Last synced:` line (update that line's date to 2026-09-26 and summary to mention BROski operator Phase 1) a new section:

```markdown
## 2026-09-26 — BROski operator Phase 1: durable async tasks on HyperFlow

`/api/v1/operator/tasks` (start / poll / approve / cancel) over `hyperflow_runs`, MCP tools
`hypercode_inspect` / `hypercode_task_get` / `hypercode_task_cancel`, real read-only
`hypercode.inspect`. Spec: `docs/superpowers/specs/2026-09-26-broski-operator-design.md`;
plan: `docs/superpowers/plans/2026-09-26-broski-operator-phase1.md`.

- Runner: cancel, context-preserving persistence, DB-backed approval decisions, restart
  recovery (`recover_runs()` in the lifespan). No migration.
- Approvals are human-JWT only; agent keys can start/read/cancel but never approve.
- Live proof (no mocks): <fill in from phase1/phase2 output: inspect handle + later result,
  cancel, approval that survived `docker restart hypercode-core`>.
- MCP live check: <done | pending key provisioning>.
- Phase 2 (`hypercode.recover`, Shepherd-gated restart) and Phase 3 (`run_tests`, RAM-gated)
  are not started.
```

Fill both `<…>` placeholders with the real results before committing; if a proof step did not run, say so plainly instead.

- [ ] **Step 12: Commit**

```bash
git add scripts/prove-operator.py docs/superpowers/specs/2026-09-26-broski-operator-design.md WHATS_DONE.md
git commit -m "docs: BROski operator Phase 1 live proof script, spec amendments, WHATS_DONE

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>"
```

- [ ] **Step 13: Whole-branch review, then stop for Bro**

Run `git log --oneline main..HEAD` and `git diff --stat main..HEAD`, do a whole-branch review (superpowers:requesting-code-review), fix findings, and report to Bro. **Do not push and do not open a PR until Bro says so.**

---

## Self-Review

**Spec coverage:** §5.1 API → Task 5. §5.2 durable approval + recovery → Tasks 2, 3. §5.3 cancel → Tasks 1, 5. §5.4 MCP surface + probe → Task 6 (approval tool intentionally dropped, amended in Task 7). §5.5 inspect tool + flow → Task 4 (`recover`/`run_tests` flows are Phases 2–3, out of Phase 1 per spec §7). §5.6 safety (no new engine, human-only approvals, allow-list) → Tasks 4 (safety gate retained), 5. §6 tests and live proof → every task + Task 7. Phase 1 boundary matches spec §7.

**Placeholder scan:** the only fill-in markers are the two proof-result blanks in Task 7 Steps 10–11 (they hold real run output that cannot exist before execution) and each step says to replace them before committing.

**Type consistency:** `history: list[dict]`, `start_at(node_id)`, `_take_persisted_decision() -> Optional[bool]`, `store_decision(db, run, *, approved, by) -> bool`, `finish_run_row(db, run, status, error)`, `RecoveryPlan(action, node_id, reason)`, `to_task_status`/`poll_interval_ms`/`progress_percent`/`build_result` names and signatures are identical wherever they appear. Persisted decision shape `{"approved","by","ts"}` is identical in Tasks 2, 3, 5. `operator_principal` returns `{"kind","name","user_id"}` in code and in the test override.

**Review Focus coverage:** items 1 (Task 1 test), 2 (Tasks 2, 5), 3 (Task 5), 4 (Task 5), 5 (Task 4), 6 (Task 6), 7 (Task 3).
