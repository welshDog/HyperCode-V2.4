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
    assert runs.store_decision(s, run, approved=True, by="bro", node="gate") is True
    assert run.state["context"]["pending_decision"]["approved"] is True
    assert run.state["context"]["pending_decision"]["node"] == "gate"
    assert runs.store_decision(s, run, approved=False, by="bro", node="gate") is False
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
