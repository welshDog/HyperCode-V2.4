import json

import pytest
from fastapi import HTTPException

from agents.goal_keeper.main import require_api_key
from agents.goal_keeper.self_improvement_framework import (
    ABTestingFramework,
    AgentMetrics,
    ImprovementProposal,
    ImprovementType,
    MetricsEngine,
)


class _FakeRedis:
    def __init__(self) -> None:
        self._kv: dict[str, str] = {}
        self._lists: dict[str, list[str]] = {}
        self._hash: dict[str, dict[str, str]] = {}
        self._streams: dict[str, list[tuple[str, dict[str, str]]]] = {}

    async def set(self, key: str, value: str) -> None:
        self._kv[key] = value

    async def get(self, key: str) -> str | None:
        return self._kv.get(key)

    async def lpush(self, key: str, value: str) -> None:
        self._lists.setdefault(key, []).insert(0, value)

    async def hset(self, name: str, key: str, value: str) -> None:
        self._hash.setdefault(name, {})[key] = value

    async def xadd(
        self,
        name: str,
        fields: dict[str, str],
        maxlen: int | None = None,
        approximate: bool = True,
    ) -> str:
        items = self._streams.setdefault(name, [])
        message_id = f"{len(items) + 1}-0"
        items.append((message_id, dict(fields)))
        if maxlen is not None and len(items) > maxlen:
            self._streams[name] = items[-maxlen:]
        return message_id


@pytest.mark.asyncio
async def test_metrics_engine_persists_and_recovers_metrics_from_redis():
    r = _FakeRedis()
    engine = MetricsEngine(r)

    await engine.record_task_completion(agent_name="agent-a", task_duration_ms=10.0, quality_score=90.0, cost_usd=0.01)
    raw = await r.get("metrics:agent-a")
    assert raw is not None
    payload = json.loads(raw)
    assert payload["agent_name"] == "agent-a"
    assert "window_start" in payload

    engine.agent_metrics.clear()
    recovered = await engine.get_agent_metrics("agent-a")
    assert recovered is not None
    assert recovered.agent_name == "agent-a"
    assert recovered.tasks_completed == 1


@pytest.mark.asyncio
async def test_ab_testing_detects_improvement_with_permutation_test():
    r = _FakeRedis()
    engine = MetricsEngine(r)

    control_agents = [f"c{i}" for i in range(4)]
    test_agents = [f"t{i}" for i in range(4)]

    for name in control_agents + test_agents:
        engine.agent_metrics[name] = AgentMetrics(agent_name=name, role="test", avg_quality_score=100.0, tasks_completed=10)

    proposal = ImprovementProposal(
        proposal_id="p1",
        agent_name="t0",
        improvement_type=ImprovementType.QUALITY,
        description="Improve quality",
        expected_impact={"quality": 0.15},
        implementation_plan=["x"],
        estimated_effort_hours=1.0,
        risk_level="low",
        created_at=engine.agent_metrics["t0"].window_start,
        proposed_by="system",
        status="pending",
    )

    ab = ABTestingFramework(r, engine)
    await ab.start_ab_test(proposal, control_agents=control_agents, test_agents=test_agents)

    for name in test_agents:
        engine.agent_metrics[name].avg_quality_score = 200.0

    ok, p_value = await ab.evaluate_ab_test("p1", p_value_threshold=0.05)
    assert ok is True
    assert p_value < 0.05


@pytest.mark.asyncio
async def test_goal_keeper_api_key_enforced_in_production(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("GOAL_KEEPER_API_KEY", raising=False)
    with pytest.raises(HTTPException) as exc:
        await require_api_key(api_key="anything")
    assert exc.value.status_code == 503

    monkeypatch.setenv("GOAL_KEEPER_API_KEY", "secret")
    with pytest.raises(HTTPException) as exc2:
        await require_api_key(api_key="wrong")
    assert exc2.value.status_code == 401

    assert await require_api_key(api_key="secret") == "secret"


@pytest.mark.asyncio
async def test_goal_keeper_api_key_never_allows_empty_in_development(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("GOAL_KEEPER_API_KEY", raising=False)

    with pytest.raises(HTTPException) as exc:
        await require_api_key(api_key="")
    assert exc.value.status_code == 401

    with pytest.raises(HTTPException) as exc2:
        await require_api_key(api_key="wrong")
    assert exc2.value.status_code == 401

    assert await require_api_key(api_key="dev-key") == "dev-key"

