# agents/mission-director/tests/test_llm_malformed_output.py
import pytest

import plan_generator


class _BadToolUse:
    type = "tool_use"
    input = {"rationale": "ok"}  # missing required requested_actions


class _BadResp:
    content = [_BadToolUse()]


class _MockAnthropic:
    class messages:
        @staticmethod
        async def create(**kwargs):
            return _BadResp()


@pytest.mark.asyncio
async def test_generate_raises_malformed_on_schema_violation(monkeypatch):
    plan_generator._client = _MockAnthropic()
    with pytest.raises(plan_generator.PlanMalformedError):
        await plan_generator.generate("do the thing")
    plan_generator._client = None


@pytest.mark.asyncio
async def test_generate_raises_generation_error_when_no_client_configured():
    plan_generator._client = None
    with pytest.raises(plan_generator.PlanGenerationError):
        await plan_generator.generate("do the thing")


@pytest.mark.asyncio
async def test_create_plan_route_returns_rejected_malformed(client, monkeypatch):
    import main

    async def _raise_malformed(goal):
        raise plan_generator.PlanMalformedError("bad output")

    async def _fake_snapshot():
        return "sha256:test"

    monkeypatch.setattr(main.plan_generator, "generate", _raise_malformed)
    monkeypatch.setattr(main, "get_snapshot_ref", lambda: "sha256:test")

    resp = await client.post("/v1/plan", json={"mission_id": "mission_t1", "goal": "x"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "rejected_malformed"
    assert body["plan_response"] is None
