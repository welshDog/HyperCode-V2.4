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
