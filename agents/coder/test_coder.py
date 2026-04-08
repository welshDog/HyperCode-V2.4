import pytest
import sys
import os
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

# Mock agents module for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from agents.coder.main import CoderAgent, AgentConfig, TaskRequest

@pytest.fixture
def agent():
    config = AgentConfig(name="test-coder", port=8002)
    return CoderAgent(config)

@pytest.fixture
def client(agent):
    with TestClient(agent.app) as c:
        yield c

@pytest.mark.asyncio
async def test_agent_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "agent": "test-coder"}

@pytest.mark.asyncio
async def test_execute_todo_app(client):
    payload = {
        "id": "task-123",
        "task": "Build a todo list app",
        "context": {}
    }
    response = client.post("/execute", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["task_id"] == "task-123"
    assert "result" in data
    assert data["result"]["status"] == "completed"
    assert "api/routes/todos.py" in data["result"]["files_created"]

@pytest.mark.asyncio
async def test_execute_health_metrics(client):
    payload = {
        "id": "task-456",
        "task": "Check system metrics",
    }
    response = client.post("/execute", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "cpu_usage" in data["result"]["metrics"]

@pytest.mark.asyncio
async def test_execute_deploy(client):
    payload = {
        "id": "task-789",
        "task": "Deploy this docker container",
    }
    response = client.post("/execute", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "analysis" in data["result"]

@pytest.mark.asyncio
async def test_execute_ollama_success(client):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        from unittest.mock import MagicMock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "def test(): pass"}
        mock_post.return_value = mock_response

        payload = {
            "id": "task-999",
            "task": "Write a python function",
        }
        response = client.post("/execute", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["result"]["code"] == "def test(): pass"

@pytest.mark.asyncio
async def test_execute_ollama_failure(client):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = Exception("Connection refused")

        payload = {
            "id": "task-999",
            "task": "Write a python function",
        }
        response = client.post("/execute", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "Connection refused" in data["error"]
