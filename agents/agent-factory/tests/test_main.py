import pytest
import os
import importlib.util
from fastapi.testclient import TestClient

_MODULE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py")
_SPEC = importlib.util.spec_from_file_location("agent_factory_main", _MODULE_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("Failed to load agent-factory main module")
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)

app = _MOD.app
REGISTRY = _MOD.REGISTRY
BLUEPRINTS = _MOD.BLUEPRINTS

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_registry():
    REGISTRY.clear()
    yield
    REGISTRY.clear()

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "factory_online", "active_agents": 0}

def test_list_blueprints():
    response = client.get("/blueprints")
    assert response.status_code == 200
    data = response.json()
    assert "frontend-specialist" in data
    assert "backend-specialist" in data

def test_spawn_agent_success():
    response = client.post("/agents/spawn?blueprint_id=frontend-specialist&count=1")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["spawned"]) == 1
    assert len(REGISTRY) == 1
    
    agent = data["spawned"][0]
    assert agent["profile"]["name"] == "Frontend Specialist"
    assert agent["status"] == "initializing"

def test_spawn_agent_invalid_blueprint():
    response = client.post("/agents/spawn?blueprint_id=invalid-id&count=1")
    assert response.status_code == 404

def test_stop_agent_success():
    # First spawn an agent
    spawn_resp = client.post("/agents/spawn?blueprint_id=backend-specialist")
    agent_id = spawn_resp.json()["spawned"][0]["id"]
    
    # Stop it
    response = client.post(f"/agents/{agent_id}/stop")
    assert response.status_code == 200
    assert response.json()["state"] == "stopped"
    assert REGISTRY[agent_id].status == "stopped"

def test_stop_agent_not_found():
    response = client.post("/agents/non-existent-id/stop")
    assert response.status_code == 404
