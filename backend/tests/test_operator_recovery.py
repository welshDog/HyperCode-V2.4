"""BROski operator — restart recovery + DB helpers."""

import asyncio
from datetime import datetime, timedelta, timezone

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


def _add(factory, run_id, flow_name, status, history, *, age_hours=None, naive=False):
    s = factory()
    extra = {}
    if age_hours is not None:
        when = datetime.now(timezone.utc) - timedelta(hours=age_hours)
        if naive:
            when = when.replace(tzinfo=None)
        extra = {"created_at": when, "updated_at": when}
    s.add(HyperFlowRun(id=run_id, flow_name=flow_name, flow_version=1, status=status,
                       current_node=None, state={"history": history}, **extra))
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


def _gate_hist():
    return [{"node": "ready", "type": "human_approval_gate",
             "status": "awaiting_approval", "result": {}}]


def test_recover_runs_isolates_run_with_missing_node(hf_db, monkeypatch):
    started = []

    async def _fake_start_at(self, node_id):
        started.append(self.run_id)
        return self

    monkeypatch.setattr(HyperFlowRunner, "start_at", _fake_start_at)
    stale = [{"node": "removed-node", "type": "tool", "status": "completed",
              "result": {"success": True}}]
    _add(hf_db, "r-stale", "hyperflow-smoke", "running", stale)
    _add(hf_db, "r-ok", "hyperflow-smoke", "awaiting_approval", _gate_hist())

    counts = asyncio.run(recover_runs())

    assert counts == {"resume": 1, "complete": 0, "fail": 1, "skip": 0}
    assert started == ["r-ok"]
    s = hf_db()
    stale_row = s.get(HyperFlowRun, "r-stale")
    assert stale_row.status == "failed" and "recovery error" in stale_row.state["error"]
    s.close()


def test_recover_runs_isolates_start_at_failure(hf_db, monkeypatch):
    started = []

    async def _fake_start_at(self, node_id):
        if self.run_id == "r-boom":
            raise RuntimeError("boom")
        started.append(self.run_id)
        return self

    monkeypatch.setattr(HyperFlowRunner, "start_at", _fake_start_at)
    for rid in ("r-a", "r-boom", "r-b"):
        _add(hf_db, rid, "hyperflow-smoke", "awaiting_approval", _gate_hist())

    counts = asyncio.run(recover_runs())

    assert counts == {"resume": 2, "complete": 0, "fail": 1, "skip": 0}
    assert sorted(started) == ["r-a", "r-b"]
    s = hf_db()
    boom = s.get(HyperFlowRun, "r-boom")
    assert boom.status == "failed" and "recovery error: RuntimeError: boom" in boom.state["error"]
    assert s.get(HyperFlowRun, "r-a").status == "awaiting_approval"
    s.close()


def test_recover_runs_survives_failing_failure_handler(hf_db, monkeypatch):
    async def _fake_start_at(self, node_id):
        return self

    monkeypatch.setattr(HyperFlowRunner, "start_at", _fake_start_at)
    monkeypatch.setattr(recovery, "_finish_row", lambda *a, **k: (_ for _ in ()).throw(OSError("db")))
    _add(hf_db, "r-ghost", "vanished-flow", "running", [])
    _add(hf_db, "r-ok", "hyperflow-smoke", "awaiting_approval", _gate_hist())

    counts = asyncio.run(recover_runs())

    assert counts == {"resume": 1, "complete": 0, "fail": 0, "skip": 0}


def _fake_start(monkeypatch):
    started = []

    async def _fake_start_at(self, node_id):
        started.append((self.run_id, node_id))
        return self

    monkeypatch.setattr(HyperFlowRunner, "start_at", _fake_start_at)
    return started


def test_recover_runs_fails_stale_run_but_resumes_fresh_gate_run(hf_db, monkeypatch):
    monkeypatch.delenv("RECOVERY_MAX_AGE_HOURS", raising=False)
    started = _fake_start(monkeypatch)
    _add(hf_db, "r-old", "hyperflow-smoke", "awaiting_approval", _gate_hist(), age_hours=72)
    _add(hf_db, "r-fresh", "hyperflow-smoke", "awaiting_approval", _gate_hist(), age_hours=1)

    counts = asyncio.run(recover_runs())

    assert counts == {"resume": 1, "complete": 0, "fail": 1, "skip": 0}
    assert started == [("r-fresh", "ready")]
    s = hf_db()
    old = s.get(HyperFlowRun, "r-old")
    assert old.status == "failed"
    assert old.state["error"] == "stale at recovery (older than 24h)"
    assert s.get(HyperFlowRun, "r-fresh").status == "awaiting_approval"
    s.close()


def test_recover_runs_stale_cutoff_handles_naive_datetimes(hf_db, monkeypatch):
    monkeypatch.delenv("RECOVERY_MAX_AGE_HOURS", raising=False)
    started = _fake_start(monkeypatch)
    _add(hf_db, "r-old", "hyperflow-smoke", "running", [], age_hours=30, naive=True)
    _add(hf_db, "r-new", "hyperflow-smoke", "awaiting_approval", _gate_hist(),
         age_hours=2, naive=True)

    counts = asyncio.run(recover_runs())

    assert counts["fail"] == 1 and counts["resume"] == 1
    assert started == [("r-new", "ready")]


def test_recover_runs_age_boundary(hf_db, monkeypatch):
    monkeypatch.delenv("RECOVERY_MAX_AGE_HOURS", raising=False)
    started = _fake_start(monkeypatch)
    _add(hf_db, "r-just-in", "hyperflow-smoke", "awaiting_approval", _gate_hist(),
         age_hours=23.9)
    _add(hf_db, "r-just-out", "hyperflow-smoke", "awaiting_approval", _gate_hist(),
         age_hours=24.1)

    counts = asyncio.run(recover_runs())

    assert counts == {"resume": 1, "complete": 0, "fail": 1, "skip": 0}
    assert started == [("r-just-in", "ready")]


def test_recover_runs_max_age_env_override(hf_db, monkeypatch):
    started = _fake_start(monkeypatch)
    _add(hf_db, "r-3h", "hyperflow-smoke", "awaiting_approval", _gate_hist(), age_hours=3)

    monkeypatch.setenv("RECOVERY_MAX_AGE_HOURS", "2")
    counts = asyncio.run(recover_runs())
    assert counts["fail"] == 1 and started == []
    s = hf_db()
    assert s.get(HyperFlowRun, "r-3h").state["error"] == "stale at recovery (older than 2h)"
    s.close()

    _add(hf_db, "r-3h-b", "hyperflow-smoke", "awaiting_approval", _gate_hist(), age_hours=3)
    monkeypatch.setenv("RECOVERY_MAX_AGE_HOURS", "48")
    counts = asyncio.run(recover_runs())
    assert counts["resume"] == 1 and started == [("r-3h-b", "ready")]


def _safety(status, node):
    return {"node": node, "type": "tool", "status": status, "result": {}}


@pytest.mark.parametrize("status", ["safety_allow", "safety_skipped"])
def test_trailing_safety_pass_entry_on_idempotent_node_resumes_there(status):
    plan = plan_recovery(FLOW, "running", [_safety(status, "a")])
    assert plan.action == "resume" and plan.node_id == "a"


@pytest.mark.parametrize("status", ["safety_allow", "safety_skipped"])
def test_trailing_safety_pass_entry_on_non_idempotent_node_fails(status):
    plan = plan_recovery(FLOW, "running", [_done("a"), _safety(status, "b")])
    assert plan.action == "fail" and plan.node_id == "b" and "not idempotent" in plan.reason


@pytest.mark.parametrize("status", ["safety_escalate", "safety_block", "safety_resolved"])
def test_trailing_safety_escalate_or_block_fails_conservatively(status):
    plan = plan_recovery(FLOW, "running", [_safety(status, "a")])
    assert plan.action == "fail" and plan.reason == "interrupted by restart"
