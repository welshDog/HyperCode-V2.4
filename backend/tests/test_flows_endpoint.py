from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.api import deps
from app.main import app


def _authed():
    def _fake_user():
        return SimpleNamespace(id=1, is_superuser=False)

    app.dependency_overrides[deps.get_current_active_user] = _fake_user


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
