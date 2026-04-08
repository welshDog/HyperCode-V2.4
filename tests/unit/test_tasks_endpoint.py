"""Unit tests for the /tasks endpoint — no live DB or Celery needed."""
import pytest
from unittest.mock import patch, MagicMock
from celery.exceptions import OperationalError as CeleryOperationalError


@pytest.fixture
def client():
    try:
        from fastapi.testclient import TestClient
        from backend.app.main import app
    except ImportError:
        from fastapi.testclient import TestClient
        from app.main import app
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Returns auth headers for a test user. Override if your app uses JWT."""
    return {"X-API-Key": "test-key"}


@patch("backend.app.api.v1.endpoints.tasks.celery_app")
@patch("backend.app.api.v1.endpoints.tasks.get_db")
def test_create_task_celery_down(mock_db, mock_celery, client, auth_headers):
    mock_celery.send_task.side_effect = CeleryOperationalError("Broker down")
    mock_db.return_value = MagicMock()
    resp = client.post(
        "/api/v1/tasks/",
        json={"title": "test task", "project_id": 1},
        headers=auth_headers,
    )
    assert resp.status_code == 503
    assert "unavailable" in resp.json().get("detail", "").lower()


@patch("backend.app.api.v1.endpoints.tasks.celery_app")
@patch("backend.app.api.v1.endpoints.tasks.get_db")
def test_create_task_success(mock_db, mock_celery, client, auth_headers):
    mock_celery.send_task.return_value = MagicMock(id="abc-123")
    mock_db.return_value = MagicMock()
    resp = client.post(
        "/api/v1/tasks/",
        json={"title": "test task", "project_id": 1},
        headers=auth_headers,
    )
    # 200 or 201 means task was created and queued
    assert resp.status_code in (200, 201)


@patch("backend.app.api.v1.endpoints.memory.rag")
def test_memory_query_chroma_down(mock_rag, client, auth_headers):
    mock_rag.query.side_effect = Exception("ChromaDB unavailable")
    resp = client.post(
        "/api/v1/memory/query",
        json={"query": "test query", "limit": 5},
        headers=auth_headers,
    )
    assert resp.status_code == 503


@patch("backend.app.api.v1.endpoints.orchestrator.httpx")
def test_orchestrator_execute_down(mock_httpx, client, auth_headers):
    mock_httpx.AsyncClient.return_value.__aenter__.return_value.post.side_effect = Exception(
        "Connection refused"
    )
    resp = client.post(
        "/api/v1/orchestrator/execute",
        json={"task": "do something"},
        headers=auth_headers,
    )
    assert resp.status_code == 503
