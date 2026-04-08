import pytest
import sys
import os
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import json

# Add parent directory to path to import main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

client = TestClient(app)

# Mock Redis
@pytest.fixture
def mock_redis():
    mock = AsyncMock()
    # Setup default behaviors
    mock.ping.return_value = True
    mock.get.return_value = None
    mock.set.return_value = True
    mock.lpush.return_value = True
    mock.publish.return_value = 1
    
    with patch("main.redis_client", mock):
        yield mock

def test_health_check(mock_redis):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "crew-orchestrator"}

def test_list_agents():
    # Pydantic v2 BaseSettings blocks setattr on non-field names,
    # so mock the entire settings object instead of individual methods.
    mock_settings = MagicMock()
    mock_settings.api_key = None  # disable auth check (dev mode)
    mock_settings.enabled_agent_keys.return_value = ["backend_specialist"]
    mock_settings.agents = {"backend_specialist": "http://backend-specialist:8003"}
    with patch("main.settings", mock_settings):
        with patch("main.redis_client", None):
            response = client.get("/agents")
    assert response.status_code == 200
    agents = response.json()
    assert isinstance(agents, list)
    agent_ids = [a["id"] for a in agents]
    assert "backend_specialist" in agent_ids


@pytest.mark.asyncio
async def test_execute_task_simple(mock_redis):
    payload = {
        "task": {
            "id": "test-task-1",
            "type": "test",
            "description": "Simple test task",
            "agent": "backend-specialist",
            "requires_approval": False
        }
    }
    
    # Setup Redis to return task details
    mock_redis.get.return_value = json.dumps({"status": "running", "progress": 0})
    
    # Mock httpx
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        # Configure the response object
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success", "output": "Task done"}
        mock_post.return_value = mock_response
        
        response = client.post("/execute", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "backend-specialist" in data["results"]

@pytest.mark.asyncio
async def test_execute_task_requires_approval(mock_redis):
    payload = {
        "task": {
            "id": "test-task-2",
            "type": "test",
            "description": "Risky task",
            "agent": "backend-specialist",
            "requires_approval": True
        }
    }
    
    # Complex side effect for Redis get
    async def get_side_effect(key):
        if "details" in key:
             return json.dumps({"status": "running", "progress": 0})
        if "approval" in key:
            # Simulate approval granted
            return json.dumps({"status": "approved"})
        return None
        
    mock_redis.get.side_effect = get_side_effect

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_post.return_value = mock_response
        
        # Patch sleep to speed up test
        with patch("asyncio.sleep", new_callable=AsyncMock): 
            response = client.post("/execute", json=payload)
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
