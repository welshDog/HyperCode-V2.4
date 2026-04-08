"""
Integration Tests — Agent API
Requires running services: docker compose up -d
"""
import pytest

pytest_plugins = ['anyio']


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agents_endpoint_returns_200(core_client):
    response = await core_client.get("/api/v1/agents")
    assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agents_response_has_agents_key(core_client):
    response = await core_client.get("/api/v1/agents")
    data = response.json()
    assert "agents" in data
    assert isinstance(data["agents"], list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_healer_health_endpoint(healer_client):
    response = await healer_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_healer_xp_status_endpoint(healer_client):
    response = await healer_client.get("/xp/status")
    assert response.status_code == 200
    data = response.json()
    assert "xp_total" in data or "xp" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_dashboard_health(dashboard_client):
    response = await dashboard_client.get("/api/health")
    assert response.status_code in (200, 503)  # 503 is acceptable if core is down
    data = response.json()
    assert "healthy" in data
    assert "timestamp" in data
