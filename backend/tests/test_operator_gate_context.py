"""BROski recover — generic runner support: tool ctx, gate show_from/plan_hash, approver evidence."""

import asyncio

import pytest

from app.agents.hyperflow.schema import FlowDefinition
from app.agents.hyperflow_runner import HyperFlowRunner, _strip_data
from app.broski_operator import tools
from app.models.hyperflow import HyperFlowRunStatus
from tests.test_hyperflow import _runner_with_io


@pytest.fixture(autouse=True)
def _safety_off(monkeypatch):
    monkeypatch.setenv("SAFETY_SHEPHERD_MODE", "off")
    monkeypatch.setattr("app.agents.hyperflow_runner.APPROVAL_POLL_SECONDS", 0.01)


def _flow():
    return FlowDefinition.model_validate(
        {
            "name": "ctxflow",
            "entry": "propose",
            "nodes": [
                {"id": "propose", "type": "tool", "tool": "local.fake_propose", "success_key": "has_proposal"},
                {"id": "approve", "type": "human_approval_gate",
                 "params": {"prompt": "ok?", "show_from": "propose"}},
                {"id": "seal", "type": "tool", "tool": "local.fake_seal"},
            ],
            "edges": [
                {"from": "propose", "to": "approve", "condition": True},
                {"from": "approve", "to": "seal"},
            ],
        }
    )


PROPOSAL = {"ok": True, "has_proposal": True,
            "proposal": {"plan": {"target": "skillweaver"}, "plan_hash": "sha256:abc", "summary": "s"}}


def _register(monkeypatch, has_proposal=True, seen=None):
    async def fake_propose(params, ctx):
        if seen is not None:
            seen["ctx"] = ctx
        return dict(PROPOSAL, has_proposal=has_proposal)

    async def fake_seal(params, ctx):
        if seen is not None:
            seen["seal_history"] = ctx["history"]
        return {"ok": True, "sealed": True}

    monkeypatch.setitem(tools.LOCAL_TOOLS, "local.fake_propose", fake_propose)
    monkeypatch.setitem(tools.LOCAL_TOOLS, "local.fake_seal", fake_seal)


def test_tools_receive_run_id_and_history_ctx(monkeypatch):
    seen = {}
    _register(monkeypatch, seen=seen)
    runner, final = _runner_with_io(_flow(), "ctx-run", monkeypatch)
    monkeypatch.setattr(runner, "_take_persisted_decision", lambda *_: True)
    asyncio.run(runner._run())
    assert seen["ctx"]["run_id"] == "ctx-run" and isinstance(seen["ctx"]["history"], list)
    assert final["status"] is HyperFlowRunStatus.COMPLETED
    assert any(e["node"] == "propose" for e in seen["seal_history"])


def test_success_key_is_surfaced_so_conditional_edge_works(monkeypatch):
    _register(monkeypatch, has_proposal=False)
    runner, final = _runner_with_io(_flow(), "sk-run", monkeypatch)
    asyncio.run(runner._run())
    assert final["status"] is HyperFlowRunStatus.COMPLETED
    assert [e["node"] for e in runner._history] == ["propose"]  # no gate: edge condition false


def test_gate_shows_context_and_plan_hash(monkeypatch):
    _register(monkeypatch)
    runner, final = _runner_with_io(_flow(), "gate-run", monkeypatch)

    async def scenario():
        runner._task = asyncio.create_task(runner._run())
        await asyncio.sleep(0.1)
        assert runner.parked_gate == "approve"
        runner.resume(True)
        await runner._task

    monkeypatch.setattr(runner, "_take_persisted_decision", lambda *_: None)
    asyncio.run(scenario())
    awaiting = [e for e in runner._history if e["status"] == "awaiting_approval"][0]
    assert awaiting["result"]["prompt"] == "ok?"
    assert awaiting["result"]["context"]["proposal"]["plan_hash"] == "sha256:abc"
    assert awaiting["result"]["plan_hash"] == "sha256:abc"


def test_completed_gate_records_approver_and_plan_hash(monkeypatch):
    _register(monkeypatch)
    runner, final = _runner_with_io(_flow(), "who-run", monkeypatch)

    def take(node_id=None):
        runner._last_decision_meta = {"by": "bro@example.com", "plan_hash": "sha256:abc"}
        return True

    monkeypatch.setattr(runner, "_take_persisted_decision", take)
    asyncio.run(runner._run())
    gate_done = [e for e in runner._history if e["node"] == "approve" and e["status"] == "completed"][0]
    assert gate_done["result"]["approved"] is True
    assert gate_done["result"]["by"] == "bro@example.com"
    assert gate_done["result"]["plan_hash"] == "sha256:abc"


def test_gate_without_show_from_is_unchanged(monkeypatch):
    from tests.operator_helpers import gate_flow

    runner, final = _runner_with_io(gate_flow(), "plain", monkeypatch)
    monkeypatch.setattr(runner, "_take_persisted_decision", lambda *_: True)
    asyncio.run(runner._run())
    awaiting = [e for e in runner._history if e["status"] == "awaiting_approval"][0]
    assert awaiting["result"] == {"prompt": "ok?"}


def test_strip_data_drops_data_and_context():
    entry = {"node": "n", "result": {"success": True, "data": {"a": 1}, "context": {"b": 2}, "plan_hash": "h"}}
    out = _strip_data(entry)
    assert out["result"] == {"success": True, "plan_hash": "h"}
    assert "data" in entry["result"] and "context" in entry["result"]  # original not mutated


def test_strip_data_drops_by_from_completed_gate_entries():
    """I1 final-review fix: a completed human_approval_gate entry has neither `data` nor

    `context` — only `by`/`plan_hash` — so it needs its own guard clause to keep the
    approver's identity out of the published/returned copy. plan_hash is not identity
    data and is intentionally kept.
    """
    entry = {"node": "approve", "result": {"ok": True, "approved": True, "by": "bro@example.com", "plan_hash": "h"}}
    out = _strip_data(entry)
    assert "by" not in out["result"]
    assert out["result"]["plan_hash"] == "h"
    assert entry["result"]["by"] == "bro@example.com"  # original not mutated


def test_take_persisted_decision_records_meta(hf_db):
    from app.models.hyperflow import HyperFlowRun

    s = hf_db()
    s.add(HyperFlowRun(id="m1", flow_name="g", flow_version=1, status="awaiting_approval",
                       current_node="gate",
                       state={"history": [], "context": {"pending_decision": {
                           "approved": True, "by": "bro", "ts": "t", "node": "gate", "plan_hash": "sha256:z"}}}))
    s.commit()
    s.close()
    from tests.operator_helpers import gate_flow

    runner = HyperFlowRunner(gate_flow(), "m1")
    assert runner._take_persisted_decision("gate") is True
    assert runner._last_decision_meta == {"by": "bro", "plan_hash": "sha256:z"}
