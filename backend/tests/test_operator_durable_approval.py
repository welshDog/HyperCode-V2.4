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
