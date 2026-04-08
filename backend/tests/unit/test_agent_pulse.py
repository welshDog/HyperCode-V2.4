import pytest


class _Response:
    def __init__(self, status_code: int, json_data: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text

    def json(self) -> dict:
        return self._json_data


@pytest.mark.asyncio
async def test_pulse_process_success_builds_metrics_and_calls_brain(monkeypatch):
    import app.agents.pulse as pulse_mod
    from app.agents.pulse import PulseAgent

    def fake_get(url: str, params: dict, timeout: int):
        return _Response(
            200,
            {
                "data": {
                    "result": [
                        {"metric": {"job": "api", "instance": "core:8000"}, "value": [0, "1"]},
                        {"metric": {"job": "redis", "instance": "redis:6379"}, "value": [0, "0"]},
                    ]
                }
            },
        )

    monkeypatch.setattr(pulse_mod.requests, "get", fake_get)

    captured: dict = {}

    class BrainStub:
        async def think(self, role: str, prompt: str, use_memory: bool = False, **kwargs) -> str:
            captured["role"] = role
            captured["prompt"] = prompt
            return "report"

    agent = PulseAgent()
    agent.brain = BrainStub()

    result = await agent.process()
    assert result == "report"
    assert captured["role"] == "System Medic"
    assert "Service: api (core:8000) -> Status: UP" in captured["prompt"]
    assert "Service: redis (redis:6379) -> Status: DOWN" in captured["prompt"]


@pytest.mark.asyncio
async def test_pulse_process_non_200_includes_error(monkeypatch):
    import app.agents.pulse as pulse_mod
    from app.agents.pulse import PulseAgent

    def fake_get(url: str, params: dict, timeout: int):
        return _Response(500, {}, "boom")

    monkeypatch.setattr(pulse_mod.requests, "get", fake_get)

    captured: dict = {}

    class BrainStub:
        async def think(self, role: str, prompt: str, use_memory: bool = False, **kwargs) -> str:
            captured["prompt"] = prompt
            return "report"

    agent = PulseAgent()
    agent.brain = BrainStub()

    result = await agent.process()
    assert result == "report"
    assert "Error fetching metrics: 500 - boom" in captured["prompt"]


@pytest.mark.asyncio
async def test_pulse_process_exception_includes_critical(monkeypatch):
    import app.agents.pulse as pulse_mod
    from app.agents.pulse import PulseAgent

    def fake_get(url: str, params: dict, timeout: int):
        raise RuntimeError("no network")

    monkeypatch.setattr(pulse_mod.requests, "get", fake_get)

    captured: dict = {}

    class BrainStub:
        async def think(self, role: str, prompt: str, use_memory: bool = False, **kwargs) -> str:
            captured["prompt"] = prompt
            return "report"

    agent = PulseAgent()
    agent.brain = BrainStub()

    result = await agent.process()
    assert result == "report"
    assert "CRITICAL: Cannot reach Prometheus!" in captured["prompt"]
