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


def test_parked_gate_set_while_parked_and_cleared_after(monkeypatch):
    runner, final = _runner_with_io(gate_flow(), "pg1", monkeypatch)
    seen = {}

    async def scenario():
        assert runner.parked_gate is None
        runner._task = asyncio.create_task(runner._run())
        await asyncio.sleep(0.05)
        seen["parked"] = runner.parked_gate
        runner.resume(True)
        await runner._task
        seen["after_approve"] = runner.parked_gate

    asyncio.run(scenario())
    assert seen == {"parked": "gate", "after_approve": None}


@pytest.mark.parametrize("action", ["reject", "cancel"])
def test_parked_gate_cleared_after_reject_and_cancel(monkeypatch, action):
    runner, final = _runner_with_io(gate_flow(), f"pg-{action}", monkeypatch)

    async def scenario():
        runner._task = asyncio.create_task(runner._run())
        await asyncio.sleep(0.05)
        assert runner.parked_gate == "gate"
        if action == "reject":
            runner.resume(False)
            await runner._task
        else:
            await runner.cancel("stop")

    asyncio.run(scenario())
    assert runner.parked_gate is None


def _seed_row(factory, run_id, status, state):
    s = factory()
    s.add(HyperFlowRun(id=run_id, flow_name="g", flow_version=1, status=status,
                       current_node=None, state=state))
    s.commit()
    s.close()


def test_late_persist_never_unterminates_a_cancelled_row(hf_db):
    """I5b: a _persist_sync landing after the CANCELLED write must not flip the row back."""
    _seed_row(hf_db, "i5b", "cancelled",
              {"history": [{"node": None, "status": "cancelled"}], "error": "stop"})
    runner = HyperFlowRunner(gate_flow(), "i5b")
    runner._history.append({"node": "gate", "status": "awaiting_approval"})
    runner._persist_sync(HyperFlowRunStatus.RUNNING, "gate", False, None)
    runner._persist_sync(HyperFlowRunStatus.AWAITING_APPROVAL, "gate", False, None)

    s = hf_db()
    run = s.get(HyperFlowRun, "i5b")
    assert run.status == "cancelled"
    assert run.state["history"] == [{"node": None, "status": "cancelled"}]  # untouched
    assert run.state["error"] == "stop"
    s.close()


def test_terminal_to_terminal_persist_still_writes(hf_db):
    _seed_row(hf_db, "i5c", "failed", {"history": []})
    runner = HyperFlowRunner(gate_flow(), "i5c")
    runner._persist_sync(HyperFlowRunStatus.CANCELLED, None, True, "late cancel")
    s = hf_db()
    run = s.get(HyperFlowRun, "i5c")
    assert run.status == "cancelled" and run.state["error"] == "late cancel"
    s.close()


def test_persist_takes_row_lock_on_read(hf_db, monkeypatch):
    """I5a: both read-modify-write paths must SELECT ... FOR UPDATE."""
    _seed_row(hf_db, "i5a", "awaiting_approval",
              {"history": [], "context": {"pending_decision": {"approved": True, "node": "gate"}}})
    calls = []
    from sqlalchemy.orm import Session

    real_get = Session.get

    def spy(self, entity, ident, **kw):
        calls.append(kw.get("with_for_update"))
        return real_get(self, entity, ident, **kw)

    monkeypatch.setattr(Session, "get", spy)
    runner = HyperFlowRunner(gate_flow(), "i5a")
    runner._persist_sync(HyperFlowRunStatus.AWAITING_APPROVAL, "gate", False, None)
    runner._take_persisted_decision("gate")
    assert calls == [True, True]


def test_live_finish_appends_terminal_history_entry(hf_db, monkeypatch):
    """M2: a live cancel/complete/fail leaves the same audit record as the DB-only path."""
    runner = HyperFlowRunner(gate_flow(), "m2")

    async def _noop(*a, **k):
        return None

    monkeypatch.setattr(runner, "_publish", _noop)
    asyncio.run(runner._finish(HyperFlowRunStatus.CANCELLED, error="because"))
    last = runner._history[-1]
    assert last["node"] is None and last["type"] == "terminal"
    assert last["status"] == "cancelled" and last["result"] == {"error": "because"}
    assert last["ts"]
    s = hf_db()
    run = s.get(HyperFlowRun, "m2")
    assert run.status == "cancelled" and run.state["history"][-1]["type"] == "terminal"
    s.close()

    runner2 = HyperFlowRunner(gate_flow(), "m2b")
    monkeypatch.setattr(runner2, "_publish", _noop)
    asyncio.run(runner2._finish(HyperFlowRunStatus.COMPLETED))
    assert runner2._history == [
        {"node": None, "type": "terminal", "status": "completed", "result": {},
         "ts": runner2._history[0]["ts"]}
    ]


class _FakeRedis:
    def __init__(self):
        self.sets, self.published = [], []

    async def set(self, key, value, ex=None):
        self.sets.append((key, value))

    async def publish(self, channel, message):
        self.published.append((channel, message))

    async def aclose(self):
        pass


def test_publish_strips_inspect_data_from_redis_message_and_snapshot(monkeypatch):
    """I6b: result.data must never reach the (unauthenticated) SSE/cache surface."""
    import json

    fake = _FakeRedis()

    async def _from_url(*a, **k):
        return fake

    monkeypatch.setattr("redis.asyncio.from_url", _from_url)
    runner = HyperFlowRunner(gate_flow(), "i6")
    secret = {"containers": ["hypercode-core"], "disk": "80%"}
    done = {"node": "inspect", "type": "tool", "status": "completed",
            "result": {"success": True, "data": secret}, "ts": "t"}
    runner._history.append(done)
    asyncio.run(runner._publish(done, HyperFlowRunStatus.RUNNING))

    ((_, snapshot),) = fake.sets
    ((_, message),) = fake.published
    assert "hypercode-core" not in snapshot and "hypercode-core" not in message
    assert json.loads(message)["result"] == {"success": True}
    assert json.loads(snapshot)["history"][0]["result"] == {"success": True}
    # stored state is not mutated
    assert runner._history[0]["result"]["data"] == secret
