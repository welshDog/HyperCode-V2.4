from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch


def _make_mock_client(return_value: dict):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = return_value
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)
    return mock_client


def test_hypersplit_requires_auth(client):
    resp = client.post("/api/v1/hypersplit", json={"task": "Do the thing", "max_microtasks": 5})
    assert resp.status_code in (401, 403)


def test_hypersplit_proxies_agent(client, monkeypatch):
    from app.api import deps
    from app.main import app

    monkeypatch.setenv("HYPER_SPLIT_AGENT_URL", "http://hyper-split-agent:8096")

    def _fake_user():
        return SimpleNamespace(id=1, is_superuser=False)

    app.dependency_overrides[deps.get_current_active_user] = _fake_user

    payload = {
        "original_task": "Big scary task",
        "microtasks": [
            {"id": 1, "title": "Step 1", "estimated_mins": 15, "priority": "high"},
            {"id": 2, "title": "Step 2", "estimated_mins": 20, "priority": "medium"},
        ],
        "total_estimated_mins": 35,
    }

    mock_client = _make_mock_client(payload)
    with patch("app.api.v1.endpoints.hypersplit.httpx.AsyncClient", return_value=mock_client):
        resp = client.post("/api/v1/hypersplit", json={"task": "Big scary task", "max_microtasks": 5})

    assert resp.status_code == 200
    assert resp.json() == payload

    app.dependency_overrides.clear()
