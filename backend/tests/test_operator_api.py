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
    hist = [{"node": "ready", "type": "human_approval_gate", "status": "awaiting_approval", "result": {}}]
    _seed(db, "ok1", "awaiting_approval", hist)
    fake = _FakeRunner()
    monkeypatch.setattr(operator_tasks, "get_runner", lambda run_id: fake)
    r = client.post(f"{BASE}/tasks/ok1/input", json={"decision": "approve"})
    assert r.status_code == 200 and r.json()["accepted"] is True
    assert fake.resumed == [True]
    db.expire_all()
    run = db.get(HyperFlowRun, "ok1")
    assert run.state["context"]["pending_decision"]["approved"] is True
    assert run.state["context"]["pending_decision"]["node"] == "ready"  # scoped to its gate
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
