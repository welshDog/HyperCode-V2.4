import pytest
import json
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path to import main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import request_approval, monitor_agent_health

@pytest.mark.asyncio
async def test_execute_endpoint_success(client, mock_redis, mock_httpx_response):
    """Test the /execute endpoint success path"""
    # Mock Redis responses
    # Redis is used for:
    # 1. Logging (lpush)
    # 2. Task details (set)
    # 3. Agent busy status (set/delete)
    # 4. Progress updates (get/set)
    
    # We mock get to return a valid JSON for task details update
    mock_redis.get.return_value = json.dumps({
        "id": "test-task",
        "status": "in_progress",
        "progress": 0
    })
    
    # Mock HTTPX for agent call
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_httpx_response
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    
    payload = {
        "task": {
            "id": "test-task",
            "type": "test",
            "description": "Run unit test",
            "agent": "qa_engineer",
            "requires_approval": False
        }
    }
    
    with patch("httpx.AsyncClient", return_value=mock_client):
        response = await client.post("/execute", json=payload)
        
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "qa_engineer" in data["results"]
    
    # Verify Redis interactions
    assert mock_redis.set.called
    assert mock_redis.lpush.called

@pytest.mark.asyncio
async def test_approval_flow_success(client, mock_redis):
    """Test approval flow where request is approved immediately"""
    # Define side effect to handle different keys
    def get_side_effect(key, *args, **kwargs):
        if "approval" in key:
            return json.dumps({"status": "approved"})
        # Default mock for task details
        return json.dumps({
            "id": "task-approval-ok",
            "status": "in_progress",
            "progress": 0,
            "agents": ["qa_engineer"]
        })
    
    mock_redis.get.side_effect = get_side_effect
    
    payload = {
        "task": {
            "id": "task-approval-ok",
            "type": "test",
            "description": "Needs approval",
            "agent": "qa_engineer",
            "requires_approval": True
        }
    }
    
    # Mock agent execution
    mock_client = AsyncMock()
    mock_client.post.return_value = MagicMock(status_code=200, json=lambda: {"status": "ok"})
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_client):
        # We also need to mock log_event to avoid errors if redis mock isn't perfect
        with patch("main.log_event", new=AsyncMock()):
             response = await client.post("/execute", json=payload)
             
    assert response.status_code == 200
    assert response.json()["status"] == "completed"

@pytest.mark.asyncio
async def test_approval_flow_rejection(client, mock_redis):
    """Test approval flow where request is rejected"""
    mock_redis.get.return_value = json.dumps({"status": "rejected"})
    
    payload = {
        "task": {
            "id": "task-approval-no",
            "type": "test",
            "description": "Bad task",
            "agent": "qa_engineer",
            "requires_approval": True
        }
    }
    
    with patch("main.log_event", new=AsyncMock()):
        response = await client.post("/execute", json=payload)
        
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"

@pytest.mark.asyncio
async def test_request_approval_timeout(mock_redis):
    """Test the request_approval helper timeout logic"""
    # We need to simulate time passing
    start_time = datetime.now()
    
    with patch("main.datetime") as mock_dt:
        # Define return values for datetime.now() calls
        # 1. Assignment of start_time
        # 2. Loop check (let's say it's > timeout)
        mock_dt.now.side_effect = [
            start_time,
            start_time + timedelta(seconds=61)
        ]
        
        # Redis returns None (no response yet)
        mock_redis.get.return_value = None
        
        # Patch redis_client in main
        with patch("main.redis_client", mock_redis):
            # Patch log_event
            with patch("main.log_event", new=AsyncMock()):
                status = await request_approval("task-timeout", "desc")
                
    assert status == "timeout"

@pytest.mark.asyncio
async def test_health_check_monitor(mock_redis):
    """Test the background health monitor"""
    # Mock httpx client for health checks
    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_client.get.return_value = mock_resp
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    
    # Patch settings to test with 1 agent
    test_agents = {"test_agent": "http://localhost:8000"}
    
    mock_settings = MagicMock()
    mock_settings.agents = test_agents
    mock_settings.enabled_agent_keys.return_value = ["test_agent"]
    with patch("main.settings", mock_settings):
        with patch("httpx.AsyncClient", return_value=mock_client):
                with patch("main.redis_client", mock_redis):
                    with patch("asyncio.sleep", side_effect=asyncio.CancelledError):
                        try:
                            await monitor_agent_health()
                        except asyncio.CancelledError:
                            pass

                        
    # Assertions
    # Check if redis.set was called with health data
    assert mock_redis.set.called
    call_args = mock_redis.set.call_args_list
    # Find the call for "system:health"
    health_call = next((call for call in call_args if call[0][0] == "system:health"), None)
    assert health_call is not None
    
    health_data = json.loads(health_call[0][1])
    assert "test_agent" in health_data
    assert health_data["test_agent"]["status"] == "healthy"

@pytest.mark.asyncio
async def test_health_check_alert(mock_redis):
    """Test health check alerts when many agents are down"""
    # Simulate 4 agents down
    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_client.get.return_value = mock_resp
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    
    agents = {f"agent_{i}": f"http://host{i}" for i in range(5)}
    
    mock_settings = MagicMock()
    mock_settings.agents = agents
    mock_settings.enabled_agent_keys.return_value = list(agents.keys())
    with patch("main.settings", mock_settings):
        with patch("httpx.AsyncClient", return_value=mock_client):
                with patch("main.redis_client", mock_redis):
                    with patch("asyncio.sleep", side_effect=asyncio.CancelledError):
                        try:
                            await monitor_agent_health()
                        except asyncio.CancelledError:
                            pass

                        
    # Should have published an alert
    assert mock_redis.publish.called
    assert mock_redis.publish.call_args[0][0] == "approval_requests"
    alert_msg = json.loads(mock_redis.publish.call_args[0][1])
    assert alert_msg["type"] == "CRITICAL_ALERT"
