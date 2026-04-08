import pytest
import sys
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock

# Mock agentx module for testing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.modules['agentx'] = __import__('agent-x')

from agentx.main import app, AgentX

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert data["status"] == "ready"

def test_info(client):
    response = client.get("/info")
    assert response.status_code == 200
    data = response.json()
    assert "hypercode_version" in data

def test_agents_list(client):
    response = client.get("/agents")
    assert response.status_code == 200
    data = response.json()
    assert "agents" in data
    assert "total" in data
    assert "healthy" in data

def test_pipeline_status(client):
    response = client.get("/pipeline/status")
    assert response.status_code == 200
    data = response.json()
    assert "running" in data

def test_llm_status(client):
    response = client.get("/llm/status")
    assert response.status_code == 200
    data = response.json()
    assert "available" in data
    assert "model_ready" in data

def test_docker_containers(client):
    with patch("agentx.main.list_containers", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = [{"name": "container1"}]
        response = client.get("/docker/containers")
        assert response.status_code == 200

def test_pipeline_run(client):
    with patch("agentx.main.AgentX.get_pipeline") as mock_get_pipeline:
        mock_pipeline = MagicMock()
        mock_pipeline.is_running = False
        mock_get_pipeline.return_value = mock_pipeline
        response = client.post("/pipeline/run", json={"dry_run": True})
        assert response.status_code == 200
        assert response.json()["status"] == "started"

def test_pipeline_history(client):
    with patch("agentx.main.AgentX.get_pipeline") as mock_get_pipeline:
        mock_pipeline = MagicMock()
        mock_pipeline.history = []
        mock_get_pipeline.return_value = mock_pipeline
        response = client.get("/pipeline/history")
        assert response.status_code == 200
        assert response.json()["total"] == 0

def test_pipeline_scan(client):
    with patch("agentx.main.AgentX.get_pipeline") as mock_get_pipeline:
        mock_pipeline = MagicMock()
        mock_score = MagicMock()
        mock_score.name = "test"
        mock_score.score = 100
        mock_score.reachable = True
        mock_score.healthy = True
        mock_score.needs_attention = False
        mock_score.issues = []
        
        # AsyncMock for the coroutine
        mock_scan_coro = AsyncMock(return_value=[mock_score])
        mock_pipeline.scan = mock_scan_coro
        
        mock_get_pipeline.return_value = mock_pipeline
        
        response = client.post("/pipeline/scan")
        assert response.status_code == 200
        assert response.json()["healthy_count"] == 1

def test_design_spec(client):
    with patch("agentx.main.design_agent_spec", new_callable=AsyncMock) as mock_design:
        from agentx.designer import AgentSpec
        mock_design.return_value = AgentSpec(name="test-agent", container_name="hyper-test", port=8000, archetype="worker", purpose="testing")
        response = client.post("/design/spec", json={"description": "testing"})
        assert response.status_code == 200
        assert response.json()["name"] == "test-agent"

def test_design_code(client):
    with patch("agentx.main.generate_agent_code", new_callable=AsyncMock) as mock_generate:
        from agentx.designer import GeneratedCode
        mock_generate.return_value = GeneratedCode(agent_name="test", code="code", dockerfile="docker", requirements="req")
        response = client.post("/design/code", json={"spec": {"name": "test", "port": 8000}})
        assert response.status_code == 200
        assert response.json()["code"] == "code"

def test_agent_status(client):
    with patch("agentx.main.container_health", new_callable=AsyncMock) as mock_health:
        mock_health.return_value = {"status": "healthy"}
        response = client.get("/agents/hyper-architect/status")
        assert response.status_code in [200, 404]

def test_spawn_agent(client):
    with patch("agentx.main.design_agent_spec", new_callable=AsyncMock) as mock_design:
        from agentx.designer import AgentSpec, GeneratedCode
        mock_design.return_value = AgentSpec(name="test-agent", container_name="hyper-test", port=8000, archetype="worker", purpose="testing")
        
        with patch("agentx.main.generate_agent_code", new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = GeneratedCode(agent_name="test-agent", code="code", dockerfile="docker", requirements="req")
            
            with patch("agentx.main.write_agent_file") as mock_write:
                mock_write.return_value = "path/to/file"
                
                response = client.post("/agents/spawn", json={"description": "testing", "auto_deploy": False})
                assert response.status_code == 202
                assert response.json()["spec"]["name"] == "test-agent"

def test_evolve_agent(client):
    with patch("agentx.main.suggest_improvement", new_callable=AsyncMock) as mock_suggest:
        mock_suggest.return_value = {"issue": "test", "improvement": "fix"}
        response = client.post("/agents/hyper-architect/evolve", json={"dry_run": True})
        assert response.status_code in [200, 404]

def test_evolve_agent_no_dry_run(client):
    with patch("agentx.main.suggest_improvement", new_callable=AsyncMock) as mock_suggest:
        mock_suggest.return_value = {"issue": "test", "improvement": "fix"}
        with patch("agentx.main.AgentX.get_pipeline") as mock_get_pipeline:
            mock_pipeline = MagicMock()
            mock_score = MagicMock()
            mock_score.name = "hyper-architect"
            mock_score.score = 100
            mock_score.issues = []
            mock_pipeline.scan = AsyncMock(return_value=[mock_score])
            mock_get_pipeline.return_value = mock_pipeline
            
            with patch("agentx.main.build_image", new_callable=AsyncMock) as mock_build:
                mock_build.return_value = MagicMock(success=True, image_tag="test:latest", error=None)
                
                with patch("agentx.main.deploy_service", new_callable=AsyncMock) as mock_deploy:
                    mock_deploy.return_value = MagicMock(success=True, error=None)
                    
                    with patch("agentx.docker_ops.wait_for_healthy", new_callable=AsyncMock) as mock_wait:
                        mock_wait.return_value = True
                        
                        response = client.post("/agents/hyper-architect/evolve", json={"dry_run": False})
                        assert response.status_code in [200, 404]

def test_rebuild_agent(client):
    with patch("agentx.main.deploy_service", new_callable=AsyncMock) as mock_deploy:
        mock_deploy.return_value = MagicMock(success=True, old_image="old", new_image="new", error=None)
        response = client.post("/agents/hyper-architect/rebuild", json={"compose_file": "docker-compose.yml"})
        assert response.status_code in [200, 404]

def test_docker_health(client):
    with patch("agentx.main.container_health", new_callable=AsyncMock) as mock_health:
        mock_health.return_value = {"status": "healthy"}
        response = client.get("/docker/health/test-container")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

def test_spawn_history(client):
    response = client.get("/agents/spawn/history")
    assert response.status_code == 200
    assert "total" in response.json()

def test_get_agent_code(client):
    with patch("builtins.open") as mock_open:
        mock_open.return_value.__enter__.return_value.read.return_value = "code"
        response = client.get("/design/code/hyper-architect")
        assert response.status_code in [200, 404]

def test_get_agent_code_not_found(client):
    response = client.get("/design/code/unknown")
    assert response.status_code == 404

def test_llm_status_with_models(client):
    with patch("agentx.designer.ollama_available", new_callable=AsyncMock) as mock_avail:
        mock_avail.return_value = True
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MagicMock(status_code=200, json=lambda: {"models": [{"name": "qwen2.5-coder:3b"}]})
            response = client.get("/llm/status")
            assert response.status_code == 200
            assert "qwen2.5-coder:3b" in response.json()["loaded_models"]


