"""BROski operator — gate context exposure + plan_hash enforcement on approve (Task 4)."""

from app.api.v1.endpoints import operator_tasks
from app.main import app
from app.models.hyperflow import HyperFlowRun

BASE = "/api/v1/operator"

GATE_HASH = "sha256:" + "a" * 64
HIST = [{"node": "ready", "type": "human_approval_gate", "status": "awaiting_approval",
         "result": {"prompt": "Approve?", "plan_hash": GATE_HASH,
                    "context": {"proposal": {"plan_hash": GATE_HASH, "summary": "restart x"}}}}]


def _as(kind="user", name="bro", user_id=1, is_superuser=True):
    app.dependency_overrides[operator_tasks.operator_principal] = lambda: {
        "kind": kind, "name": name, "user_id": user_id if kind == "user" else None,
        "is_superuser": is_superuser if kind == "user" else False,
    }


def _seed(db, run_id, run_status, history=None, flow="hyperflow-smoke", state_extra=None,
          current_node=None):
    state = {"history": history or []}
    state.update(state_extra or {})
    db.add(HyperFlowRun(id=run_id, flow_name=flow, flow_version=1, status=run_status,
                        current_node=current_node, state=state))
    db.commit()


def _no_pending(db, run_id):
    db.expire_all()
    return "pending_decision" not in (db.get(HyperFlowRun, run_id).state.get("context") or {})


def test_get_exposes_context_and_plan_hash(client, db):
    _as()
    _seed(db, "p1", "awaiting_approval", HIST, current_node="ready")
    body = client.get(f"{BASE}/tasks/p1").json()
    approval = body["inputRequests"]["approval"]
    assert approval["plan_hash"] == GATE_HASH
    assert approval["context"]["proposal"]["summary"] == "restart x"


def test_approve_requires_plan_hash(client, db):
    _as()
    _seed(db, "p2", "awaiting_approval", HIST, current_node="ready")
    r = client.post(f"{BASE}/tasks/p2/input", json={"decision": "approve"})
    assert r.status_code == 422
    assert r.json()["detail"]["error"] == "plan_hash_required"
    assert _no_pending(db, "p2")


def test_approve_with_wrong_hash_409(client, db):
    _as()
    _seed(db, "p3", "awaiting_approval", HIST, current_node="ready")
    r = client.post(
        f"{BASE}/tasks/p3/input",
        json={"decision": "approve", "plan_hash": "sha256:" + "b" * 64},
    )
    assert r.status_code == 409
    assert r.json()["detail"]["error"] == "plan_hash_mismatch"
    assert _no_pending(db, "p3")


def test_approve_with_non_string_hash_422(client, db):
    _as()
    _seed(db, "p4", "awaiting_approval", HIST, current_node="ready")
    r = client.post(f"{BASE}/tasks/p4/input", json={"decision": "approve", "plan_hash": 5})
    assert r.status_code == 422
    assert _no_pending(db, "p4")


def test_approve_with_right_hash_stores_it(client, db, monkeypatch):
    _as()
    monkeypatch.setattr(operator_tasks, "get_runner", lambda run_id: None)
    _seed(db, "p5", "awaiting_approval", HIST, current_node="ready")
    r = client.post(f"{BASE}/tasks/p5/input", json={"decision": "approve", "plan_hash": GATE_HASH})
    assert r.status_code == 200
    db.expire_all()
    run = db.get(HyperFlowRun, "p5")
    assert run.state["context"]["pending_decision"]["plan_hash"] == GATE_HASH
    assert run.state["context"]["pending_decision"]["node"] == "ready"


def test_reject_needs_no_hash(client, db, monkeypatch):
    _as()
    monkeypatch.setattr(operator_tasks, "get_runner", lambda run_id: None)
    _seed(db, "p6", "awaiting_approval", HIST, current_node="ready")
    r = client.post(f"{BASE}/tasks/p6/input", json={"decision": "reject"})
    assert r.status_code == 200
    db.expire_all()
    run = db.get(HyperFlowRun, "p6")
    assert run.state["context"]["pending_decision"]["approved"] is False


def test_gate_without_plan_hash_unchanged(client, db, monkeypatch):
    _as()
    monkeypatch.setattr(operator_tasks, "get_runner", lambda run_id: None)
    hist = [{"node": "ready", "type": "human_approval_gate", "status": "awaiting_approval",
             "result": {"prompt": "Approve?"}}]
    _seed(db, "p7", "awaiting_approval", hist, current_node="ready")
    approval = client.get(f"{BASE}/tasks/p7").json()["inputRequests"]["approval"]
    assert "context" not in approval and "plan_hash" not in approval
    r = client.post(f"{BASE}/tasks/p7/input", json={"decision": "approve"})
    assert r.status_code == 200
    db.expire_all()
    pending = db.get(HyperFlowRun, "p7").state["context"]["pending_decision"]
    assert "plan_hash" not in pending


def test_not_awaiting_input_takes_priority_over_hash_check(client, db):
    _as()
    _seed(db, "p10", "running")
    r = client.post(f"{BASE}/tasks/p10/input", json={"decision": "approve"})
    assert r.status_code == 409
    assert r.json()["detail"]["error"] == "not_awaiting_input"


def test_gate_mismatch_takes_priority_over_hash_check(client, db):
    _as()
    _seed(db, "p11", "awaiting_approval", HIST, current_node="ready")
    r = client.post(
        f"{BASE}/tasks/p11/input",
        json={"decision": "approve", "node": "somewhere-else", "plan_hash": GATE_HASH},
    )
    assert r.status_code == 409
    assert r.json()["detail"] == {"error": "gate_mismatch", "expected": "ready"}
    assert _no_pending(db, "p11")


def test_plain_gate_ignores_client_sent_plan_hash_on_approve(client, db, monkeypatch):
    """Fix round 1: an unverified plan_hash must never be persisted for a plain gate."""
    _as()
    monkeypatch.setattr(operator_tasks, "get_runner", lambda run_id: None)
    hist = [{"node": "ready", "type": "human_approval_gate", "status": "awaiting_approval",
             "result": {"prompt": "Approve?"}}]
    _seed(db, "p12", "awaiting_approval", hist, current_node="ready")
    r = client.post(
        f"{BASE}/tasks/p12/input",
        json={"decision": "approve", "plan_hash": "sha256:" + "c" * 64},
    )
    assert r.status_code == 200
    db.expire_all()
    pending = db.get(HyperFlowRun, "p12").state["context"]["pending_decision"]
    assert "plan_hash" not in pending


def test_reject_never_stores_a_sent_plan_hash(client, db, monkeypatch):
    """Fix round 1: rejects never persist a client-sent plan_hash, even for a hashed gate."""
    _as()
    monkeypatch.setattr(operator_tasks, "get_runner", lambda run_id: None)
    _seed(db, "p13", "awaiting_approval", HIST, current_node="ready")
    r = client.post(f"{BASE}/tasks/p13/input", json={"decision": "reject", "plan_hash": GATE_HASH})
    assert r.status_code == 200
    db.expire_all()
    pending = db.get(HyperFlowRun, "p13").state["context"]["pending_decision"]
    assert pending["approved"] is False
    assert "plan_hash" not in pending


def test_agent_key_still_403(client, db):
    _as(kind="agent", name="hypercode-mcp-server")
    _seed(db, "p8", "awaiting_approval", HIST, current_node="ready")
    r = client.post(f"{BASE}/tasks/p8/input", json={"decision": "approve", "plan_hash": GATE_HASH})
    assert r.status_code == 403


def test_non_superuser_still_403(client, db):
    _as(is_superuser=False)
    _seed(db, "p9", "awaiting_approval", HIST, current_node="ready")
    r = client.post(f"{BASE}/tasks/p9/input", json={"decision": "approve", "plan_hash": GATE_HASH})
    assert r.status_code == 403
