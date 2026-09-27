from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.api import deps
from app.main import app


def _authed():
    def _fake_user():
        return SimpleNamespace(id=1, is_superuser=False)

    app.dependency_overrides[deps.get_current_active_user] = _fake_user


@pytest.fixture(autouse=True)
def _default_threshold(monkeypatch):
    monkeypatch.delenv("HYPERFLOW_MATCH_THRESHOLD", raising=False)


def test_description_matches_and_runs_flow(client):
    _authed()
    try:
        with patch(
            "app.api.v1.endpoints.flows.start_flow_run",
            new=AsyncMock(return_value=None),
        ) as mock_start:
            resp = client.post(
                "/api/v1/flows/runs",
                json={"description": "design and scaffold a new agent"},
            )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert body["flow"] == "implement-new-agent"
    assert body["matched_flow"] == "implement-new-agent"
    assert 0.0 < body["match_score"] <= 1.0
    mock_start.assert_awaited_once()
    called_flow = mock_start.await_args.args[0]
    assert called_flow.name == "implement-new-agent"


def test_vague_description_returns_422_with_candidates(client):
    _authed()
    try:
        resp = client.post(
            "/api/v1/flows/runs",
            json={"description": "completely unrelated weather forecast request"},
        )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["error"] == "no_confident_flow_match"
    assert len(detail["candidates"]) >= 1
    assert all({"flow", "score", "intent"} <= set(c.keys()) for c in detail["candidates"])


def test_explicit_flow_wins_over_description(client):
    _authed()
    try:
        with patch(
            "app.api.v1.endpoints.flows.start_flow_run",
            new=AsyncMock(return_value=None),
        ) as mock_start:
            resp = client.post(
                "/api/v1/flows/runs",
                json={
                    "flow": "hyperflow-smoke",
                    "description": "design and scaffold a new agent",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert body["flow"] == "hyperflow-smoke"
    assert "matched_flow" not in body
    called_flow = mock_start.await_args.args[0]
    assert called_flow.name == "hyperflow-smoke"


def test_neither_flow_nor_description_returns_422(client):
    _authed()
    try:
        resp = client.post("/api/v1/flows/runs", json={})
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 422


def test_non_string_description_returns_422(client):
    _authed()
    try:
        resp = client.post("/api/v1/flows/runs", json={"description": 42})
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 422


# ── I2: legacy resume vs operator rules ─────────────────────────────────────

from app.models.hyperflow import HyperFlowRun  # noqa: E402


def _seed_run(db, run_id, flow, status="awaiting_approval", history=None):
    db.add(HyperFlowRun(id=run_id, flow_name=flow, flow_version=1, status=status,
                        current_node="ready", state={"history": history or []}))
    db.commit()


class _Runner:
    def __init__(self, parked_gate):
        self.parked_gate = parked_gate
        self.resumed = []

    def resume(self, approved):
        self.resumed.append(approved)


def _resume(client, run_id, runner):
    _authed()
    try:
        with patch("app.api.v1.endpoints.flows.get_runner", return_value=runner):
            return client.post(f"/api/v1/flows/runs/{run_id}/resume", json={"approved": True})
    finally:
        app.dependency_overrides.pop(deps.get_current_active_user, None)


def test_legacy_resume_refuses_operator_flow_runs(client, db):
    _seed_run(db, "op1", "hyperflow-smoke")  # operator-catalog flow
    runner = _Runner("ready")
    resp = _resume(client, "op1", runner)
    assert resp.status_code == 409
    assert resp.json()["detail"] == {"error": "use_operator_api"}
    assert runner.resumed == []


def test_legacy_resume_404_for_unknown_run(client):
    assert _resume(client, "nope", _Runner("ready")).status_code == 404


def test_legacy_resume_requires_runner_parked_at_gate(client, db):
    _seed_run(db, "lg1", "implement-new-agent")
    not_parked = _Runner(None)
    resp = _resume(client, "lg1", not_parked)
    assert resp.status_code == 409 and "not awaiting approval" in resp.json()["detail"]
    assert not_parked.resumed == []
    resp = _resume(client, "lg1", None)  # no live runner in this worker
    assert resp.status_code == 409 and "not awaiting approval" in resp.json()["detail"]


def test_legacy_resume_normal_path_still_works(client, db):
    _seed_run(db, "lg2", "implement-new-agent")
    runner = _Runner("design_review")
    resp = _resume(client, "lg2", runner)
    assert resp.status_code == 200
    assert resp.json() == {"run_id": "lg2", "approved": True}
    assert runner.resumed == [True]


# ── I6a: no inspect data on the unauthenticated legacy read surface ─────────

_INSPECT_HISTORY = [
    {"node": "inspect", "type": "tool", "status": "completed", "ts": "t",
     "result": {"success": True, "data": {"containers": ["hypercode-core"]}}},
    {"node": None, "type": "terminal", "status": "completed", "result": {}, "ts": "t2"},
]


def test_legacy_get_run_and_active_strip_result_data(client, db):
    import copy

    _seed_run(db, "i6a", "operator-inspect", status="running",
              history=copy.deepcopy(_INSPECT_HISTORY))
    body = client.get("/api/v1/flows/runs/i6a").json()
    assert body["history"][0]["result"] == {"success": True}
    assert body["history"][0]["node"] == "inspect"
    assert "hypercode-core" not in str(body)
    active = client.get("/api/v1/flows/active").json()
    assert "hypercode-core" not in str(active) and active["count"] == 1
    # stored state untouched, operator API still returns the report
    db.expire_all()
    assert db.get(HyperFlowRun, "i6a").state["history"][0]["result"]["data"] == {
        "containers": ["hypercode-core"]
    }
    _seed_run(db, "i6b", "operator-inspect", status="completed",
              history=copy.deepcopy(_INSPECT_HISTORY))
    from app.api.v1.endpoints import operator_tasks

    app.dependency_overrides[operator_tasks.operator_principal] = lambda: {
        "kind": "user", "name": "bro", "user_id": 1, "is_superuser": True}
    op = client.get("/api/v1/operator/tasks/i6b").json()
    assert op["result"]["report"] == {"containers": ["hypercode-core"]}


_GATE_CONTEXT_HISTORY = [
    {"node": "approve", "type": "human_approval_gate", "status": "awaiting_approval", "ts": "t",
     "result": {"prompt": "ok?", "context": {"plan": {"target": "skillweaver"}},
                "plan_hash": "sha256:abc"}},
    {"node": None, "type": "terminal", "status": "completed", "result": {}, "ts": "t2"},
]


def test_legacy_get_run_strips_result_context(client, db):
    import copy

    _seed_run(db, "i6c", "operator-inspect", status="awaiting_approval",
              history=copy.deepcopy(_GATE_CONTEXT_HISTORY))
    body = client.get("/api/v1/flows/runs/i6c").json()
    assert body["history"][0]["result"] == {"prompt": "ok?", "plan_hash": "sha256:abc"}
    assert "context" not in body["history"][0]["result"]
    assert "skillweaver" not in str(body)
