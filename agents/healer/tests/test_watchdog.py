import pytest
from unittest.mock import AsyncMock


class _FakeResponse:
    def __init__(self, status_code: int, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class _FakeAsyncClient:
    def __init__(self, responses):
        self._responses = responses

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, headers=None):
        return self._responses[("GET", url)]

    async def post(self, url, headers=None, json=None):
        return self._responses[("POST", url)]


@pytest.mark.asyncio
async def test_watchdog_cycle_heals_unhealthy_agents(monkeypatch):
    import healer.main as hm

    hm.WATCHDOG_SMOKE_API_KEY = "bench-key"
    hm.ORCHESTRATOR_URL = "http://crew-orchestrator:8080"

    responses = {
        ("GET", "http://crew-orchestrator:8080/agents"): _FakeResponse(
            200,
            [
                {"id": "backend_specialist", "url": "http://backend-specialist:8003"},
                {"id": "frontend_specialist", "url": "http://frontend-specialist:8012"},
            ],
        ),
        ("POST", "http://crew-orchestrator:8080/execute/smoke"): _FakeResponse(
            200,
            {
                "agents": {
                    "backend_specialist": {"status": "down"},
                    "frontend_specialist": {"status": "healthy"},
                }
            },
        ),
    }

    monkeypatch.setattr(hm.httpx, "AsyncClient", lambda timeout=10.0: _FakeAsyncClient(responses))

    heal_mock = AsyncMock()
    monkeypatch.setattr(hm, "attempt_heal_agent", heal_mock)

    await hm.watchdog_cycle()

    heal_mock.assert_awaited_once_with(
        "backend-specialist",
        "http://backend-specialist:8003",
        attempts=2,
        timeout=5.0,
        force_restart=False,
    )
