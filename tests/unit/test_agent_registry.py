"""
Unit Tests — Agent Registry Service
Covers: registration, status updates, XP awarding, deregistration
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock


class MockAgentRegistry:
    """Stub registry for unit testing without Redis/Postgres."""

    def __init__(self):
        self._agents: dict[str, dict] = {}

    async def register(self, agent_id: str, name: str, port: int) -> dict:
        entry = {
            "id": agent_id,
            "name": name,
            "port": port,
            "status": "idle",
            "xp": 0,
            "level": 1,
            "xp_to_next_level": 500,
            "coins": 0,
            "registered_at": datetime.now(timezone.utc).isoformat(),
        }
        self._agents[agent_id] = entry
        return entry

    async def update_status(self, agent_id: str, status: str) -> dict:
        if agent_id not in self._agents:
            raise KeyError(f"Agent not found: {agent_id}")
        self._agents[agent_id]["status"] = status
        return self._agents[agent_id]

    async def award_xp(self, agent_id: str, xp: int) -> dict:
        if agent_id not in self._agents:
            raise KeyError(f"Agent not found: {agent_id}")
        self._agents[agent_id]["xp"] += xp
        # Level up logic
        threshold = self._agents[agent_id]["xp_to_next_level"]
        if self._agents[agent_id]["xp"] >= threshold:
            self._agents[agent_id]["level"] += 1
            self._agents[agent_id]["xp"] -= threshold
            self._agents[agent_id]["xp_to_next_level"] = threshold + 250
        return self._agents[agent_id]

    async def list_agents(self) -> list[dict]:
        return list(self._agents.values())

    async def deregister(self, agent_id: str) -> bool:
        if agent_id not in self._agents:
            return False
        del self._agents[agent_id]
        return True


@pytest.fixture
def registry() -> MockAgentRegistry:
    return MockAgentRegistry()


@pytest.mark.asyncio
async def test_register_agent(registry):
    result = await registry.register("healer", "Healer Agent", 8008)
    assert result["id"] == "healer"
    assert result["name"] == "Healer Agent"
    assert result["status"] == "idle"
    assert result["xp"] == 0
    assert result["level"] == 1


@pytest.mark.asyncio
async def test_update_status_healthy(registry):
    await registry.register("healer", "Healer Agent", 8008)
    result = await registry.update_status("healer", "healthy")
    assert result["status"] == "healthy"


@pytest.mark.asyncio
async def test_update_status_unknown_agent(registry):
    with pytest.raises(KeyError):
        await registry.update_status("nonexistent", "healthy")


@pytest.mark.asyncio
async def test_award_xp_accumulates(registry):
    await registry.register("healer", "Healer Agent", 8008)
    await registry.award_xp("healer", 100)
    result = await registry.award_xp("healer", 50)
    assert result["xp"] == 150


@pytest.mark.asyncio
async def test_award_xp_triggers_level_up(registry):
    await registry.register("healer", "Healer Agent", 8008)
    result = await registry.award_xp("healer", 500)
    assert result["level"] == 2
    assert result["xp"] == 0  # reset after level up
    assert result["xp_to_next_level"] == 750


@pytest.mark.asyncio
async def test_list_agents_empty(registry):
    agents = await registry.list_agents()
    assert agents == []


@pytest.mark.asyncio
async def test_list_agents_multiple(registry):
    await registry.register("healer", "Healer", 8008)
    await registry.register("agent-x", "Agent X", 9000)
    agents = await registry.list_agents()
    assert len(agents) == 2
    ids = {a["id"] for a in agents}
    assert ids == {"healer", "agent-x"}


@pytest.mark.asyncio
async def test_deregister_agent(registry):
    await registry.register("healer", "Healer", 8008)
    result = await registry.deregister("healer")
    assert result is True
    agents = await registry.list_agents()
    assert agents == []


@pytest.mark.asyncio
async def test_deregister_nonexistent(registry):
    result = await registry.deregister("ghost")
    assert result is False


@pytest.mark.asyncio
async def test_status_transitions(registry):
    await registry.register("healer", "Healer", 8008)
    for status in ["healthy", "warning", "error", "healing", "idle"]:
        result = await registry.update_status("healer", status)
        assert result["status"] == status
