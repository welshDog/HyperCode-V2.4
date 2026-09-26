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

    def _take(*_):
        calls["n"] += 1
        return True if calls["n"] >= 2 else None

    monkeypatch.setattr(runner, "_take_persisted_decision", _take)
    asyncio.run(runner._run())
    assert final["status"] is HyperFlowRunStatus.COMPLETED


def test_gate_honours_persisted_rejection(monkeypatch):
    runner, final = _runner_with_io(gate_flow(), "d2", monkeypatch)
    monkeypatch.setattr(runner, "_take_persisted_decision", lambda *_: False)
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
    monkeypatch.setattr(runner, "_take_persisted_decision", lambda *_: True)
    asyncio.run(runner._run("b"))
    assert [e["node"] for e in runner._history] == ["b", "b"]  # awaiting_approval + completed
    assert final["status"] is HyperFlowRunStatus.COMPLETED


def test_persisted_decision_stale_if_scoped_to_different_node(hf_db, monkeypatch):
    """A decision for node 'a' should not approve gate 'b'; gate keeps waiting."""
    # Manually create row with stale decision (scoped to different node)
    state = {"history": []}
    ctx = {"pending_decision": {"approved": True, "by": "test", "ts": "t", "node": "a"}}
    state["context"] = ctx
    s = hf_db()
    s.add(
        HyperFlowRun(
            id="d5", flow_name="g", flow_version=1,
            status="awaiting_approval", current_node="b", state=state,
        )
    )
    s.commit()
    s.close()

    flow = two_gate_flow()
    runner, final = _runner_with_io(flow, "d5", monkeypatch)
    # Return stale decision on first call (will be discarded), matching on second
    calls = {"n": 0}
    def _take(node_id):
        calls["n"] += 1
        if calls["n"] == 1:
            # First poll: decision scoped to 'a', we're at 'b' → return None
            return None
        else:
            # After timeout, second poll: matching decision for gate 'b'
            return True
    monkeypatch.setattr(runner, "_take_persisted_decision", _take)
    asyncio.run(runner._run("b"))
    # Gate keeps waiting → times out, re-polls → gets matching decision → completes
    assert final["status"] is HyperFlowRunStatus.COMPLETED


def test_persisted_decision_accepted_if_node_matches(hf_db):
    """A decision scoped to the gate node should be accepted immediately."""
    # Manually create row with decision scoped to matching node
    state = {"history": []}
    ctx = {"pending_decision": {"approved": True, "by": "test", "ts": "t", "node": "gate"}}
    state["context"] = ctx
    s = hf_db()
    s.add(
        HyperFlowRun(
            id="d6", flow_name="g", flow_version=1,
            status="awaiting_approval", current_node="gate", state=state,
        )
    )
    s.commit()
    s.close()

    runner = HyperFlowRunner(gate_flow(), "d6")
    assert runner._take_persisted_decision("gate") is True
    # Verify it was cleared
    assert runner._take_persisted_decision("gate") is None
    s = hf_db()
    ctx = s.get(HyperFlowRun, "d6").state["context"]
    s.close()
    assert "pending_decision" not in ctx


def test_drain_path_resume_wins_drops_persisted_decision(hf_db, monkeypatch):
    """resume(True) signal wins race; persisted decision is discarded on drain call."""
    # Seed DB with a decision
    state = {"history": []}
    ctx = {"pending_decision": {"approved": True, "by": "test", "ts": "t", "node": "gate"}}
    state["context"] = ctx
    s = hf_db()
    s.add(
        HyperFlowRun(
            id="d7", flow_name="g", flow_version=1,
            status="awaiting_approval", current_node="gate", state=state,
        )
    )
    s.commit()
    s.close()

    # Create runner with selective mocking: I/O but NOT _take_persisted_decision
    runner = HyperFlowRunner(gate_flow(), "d7")

    async def _noop(*a, **k):
        return None

    monkeypatch.setattr(runner, "_persist", _noop)
    monkeypatch.setattr(runner, "_publish", _noop)
    monkeypatch.setattr(runner, "_publish_approval_request", _noop)

    final = {}
    async def _finish(status, error=None):
        final["status"] = status
        final["error"] = error

    async def _green(node):
        return {"ok": True, "green": True}

    monkeypatch.setattr(runner, "_finish", _finish)
    monkeypatch.setattr(runner, "_dispatch", _green)
    # Note: NOT mocking _take_persisted_decision, so it uses the real implementation

    async def scenario():
        runner._task = asyncio.create_task(runner._run())
        await asyncio.sleep(0.02)  # Let it reach the gate
        runner.resume(True)  # In-memory signal wins
        await runner._task

    asyncio.run(scenario())
    # The drain call should have cleared the persisted decision
    s = hf_db()
    run = s.get(HyperFlowRun, "d7")
    s.close()
    assert "pending_decision" not in (run.state.get("context") or {})
    assert final["status"] is HyperFlowRunStatus.COMPLETED


def test_start_at_registers_and_cleans_up(monkeypatch):
    """start_at() should register in _ACTIVE, run from node, and clean up after."""
    from app.agents.hyperflow_runner import _ACTIVE, get_runner
    runner, final = _runner_with_io(two_gate_flow(), "s2", monkeypatch)
    monkeypatch.setattr(runner, "_take_persisted_decision", lambda *_: True)

    async def scenario():
        # Before start_at: not in _ACTIVE
        assert "s2" not in _ACTIVE
        # Call start_at
        await runner.start_at("b")
        # Should now be registered
        assert get_runner("s2") is runner
        # Wait for completion
        await runner._task
        # After completion: should be cleaned up
        assert "s2" not in _ACTIVE

    asyncio.run(scenario())
    # Verify it ran from "b", not from entry
    assert [e["node"] for e in runner._history] == ["b", "b"]
    assert final["status"] is HyperFlowRunStatus.COMPLETED


def test_malformed_decision_cleared_and_returns_none(hf_db):
    """A non-dict pending_decision (malformed) should be cleared and return None."""
    state = {"history": []}
    ctx = {"pending_decision": "not-a-dict"}  # Malformed: string, not dict
    state["context"] = ctx
    s = hf_db()
    s.add(
        HyperFlowRun(
            id="d8", flow_name="g", flow_version=1,
            status="awaiting_approval", current_node="gate", state=state,
        )
    )
    s.commit()
    s.close()

    runner = HyperFlowRunner(gate_flow(), "d8")
    # Should return None for malformed data
    assert runner._take_persisted_decision("gate") is None
    # Should be cleared (not stuck in an infinite loop)
    assert runner._take_persisted_decision("gate") is None
    s = hf_db()
    ctx = s.get(HyperFlowRun, "d8").state["context"]
    s.close()
    assert "pending_decision" not in ctx
