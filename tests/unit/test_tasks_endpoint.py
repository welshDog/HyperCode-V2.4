"""Unit tests for the /tasks, /memory and /orchestrator failure paths.

No live DB, Celery, ChromaDB or orchestrator is needed: auth and the database
are replaced through FastAPI dependency overrides, and the downstream services
are patched where the endpoints actually look them up.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from celery.exceptions import OperationalError as CeleryOperationalError


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.api import deps
    from app.db.session import get_db
    from app.main import app

    user = MagicMock(id=1, is_superuser=True, is_active=True)
    db = MagicMock()

    def _refresh(task):
        # The endpoint returns the refreshed row; fill what the DB would.
        task.id = 7
        task.created_at = datetime.now(timezone.utc)

    db.refresh.side_effect = _refresh

    app.dependency_overrides[deps.get_current_active_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(deps.get_current_active_user, None)
        app.dependency_overrides.pop(get_db, None)


# celery_app is imported inside create_task, so patch it at its home module.
@patch("app.core.celery_app.celery_app")
def test_create_task_celery_down(mock_celery, client):
    mock_celery.send_task.side_effect = CeleryOperationalError("Broker down")
    resp = client.post("/api/v1/tasks/", json={"title": "test task", "project_id": 1})
    assert resp.status_code == 503
    assert "unavailable" in resp.json().get("detail", "").lower()


@patch("app.core.celery_app.celery_app")
def test_create_task_success(mock_celery, client):
    mock_celery.send_task.return_value = MagicMock(id="abc-123")
    resp = client.post("/api/v1/tasks/", json={"title": "test task", "project_id": 1})
    assert resp.status_code == 200
    assert resp.json()["title"] == "test task"
    mock_celery.send_task.assert_called_once()


@patch("app.api.v1.endpoints.memory.rag")
def test_memory_query_chroma_down(mock_rag, client):
    mock_rag.query.side_effect = Exception("ChromaDB unavailable")
    resp = client.post("/api/v1/memory/query", json={"query": "test query", "limit": 5})
    assert resp.status_code == 503


@patch("app.api.v1.endpoints.orchestrator.httpx")
def test_orchestrator_execute_down(mock_httpx, client):
    # The endpoint uses "async with httpx.AsyncClient(...) as client".
    async_client = MagicMock()
    async_client.post = AsyncMock(side_effect=Exception("Connection refused"))
    mock_httpx.AsyncClient.return_value.__aenter__ = AsyncMock(return_value=async_client)
    mock_httpx.AsyncClient.return_value.__aexit__ = AsyncMock(return_value=False)
    resp = client.post("/api/v1/orchestrator/execute", json={"task": "do something"})
    assert resp.status_code == 503


def test_unauthenticated_request_is_rejected():
    """Without the dependency overrides the endpoints must refuse the call."""
    from fastapi.testclient import TestClient

    from app.main import app

    resp = TestClient(app).post(
        "/api/v1/tasks/", json={"title": "test task", "project_id": 1}
    )
    assert resp.status_code in (401, 403)
