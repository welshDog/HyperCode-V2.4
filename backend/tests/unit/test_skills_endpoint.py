import pytest
from fastapi.testclient import TestClient


SAMPLE_CATALOG = [
    {
        "name": "hypercode-broski-discord-bot",
        "description": "Builds and maintains the BROski Discord bot including moderation commands.",
    },
    {
        "name": "cve-trivy-scan",
        "description": "Scans containers for CVEs with Trivy.",
    },
]


@pytest.fixture
def api_client(monkeypatch):
    """A TestClient for just the app, with the skill catalog pinned to a fixture."""
    from app.main import app
    from app.api.v1.endpoints import skills as skills_mod

    monkeypatch.setattr(skills_mod, "_load_catalog", lambda: SAMPLE_CATALOG)
    with TestClient(app) as client:
        yield client


def test_search_missing_goal_returns_422(api_client):
    """Test search missing goal returns 422."""
    resp = api_client.post("/api/v1/skills/search", json={})
    assert resp.status_code == 422


def test_search_falls_back_when_api_key_unset(api_client, monkeypatch):
    """Test search falls back when api key unset."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", None)

    resp = api_client.post("/api/v1/skills/search", json={"goal": "check for CVEs"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["usedFallback"] is True
    assert body["error"]
    assert len(body["matches"]) > 0
    assert any(m["name"] == "cve-trivy-scan" for m in body["matches"])


def test_search_falls_back_when_openrouter_chat_raises(api_client, monkeypatch):
    """Test search falls back when openrouter_chat raises RuntimeError."""
    from app.core.config import settings
    from app.api.v1.endpoints import skills as skills_mod

    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "test-key")

    async def _raise(*args, **kwargs):
        raise RuntimeError("OpenRouter error 500: boom")

    monkeypatch.setattr(skills_mod, "openrouter_chat", _raise)

    resp = api_client.post("/api/v1/skills/search", json={"goal": "deploy a discord bot"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["usedFallback"] is True
    assert len(body["matches"]) > 0


def test_search_falls_back_on_circuit_breaker_open(api_client, monkeypatch):
    """Test search falls back when the circuit breaker is open."""
    from app.core.config import settings
    from app.core.circuit_breaker import CircuitBreakerOpen
    from app.api.v1.endpoints import skills as skills_mod

    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "test-key")

    async def _raise(*args, **kwargs):
        raise CircuitBreakerOpen("llm-router", 12.0)

    monkeypatch.setattr(skills_mod, "openrouter_chat", _raise)

    resp = api_client.post("/api/v1/skills/search", json={"goal": "deploy a discord bot"})

    assert resp.status_code == 200
    assert resp.json()["usedFallback"] is True


def test_search_falls_back_on_network_error(api_client, monkeypatch):
    """Test search falls back (never 5xx) when openrouter_chat raises a raw
    httpx network error — these are not RuntimeError/CircuitBreakerOpen, so
    this specifically guards the broad `except Exception` in search_skills."""
    import httpx
    from app.core.config import settings
    from app.api.v1.endpoints import skills as skills_mod

    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "test-key")

    async def _raise(*args, **kwargs):
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(skills_mod, "openrouter_chat", _raise)

    resp = api_client.post("/api/v1/skills/search", json={"goal": "deploy a discord bot"})

    assert resp.status_code == 200
    assert resp.json()["usedFallback"] is True


def test_search_falls_back_on_non_json_response(api_client, monkeypatch):
    """Test search falls back when the LLM returns non-JSON text."""
    from app.core.config import settings
    from app.api.v1.endpoints import skills as skills_mod

    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "test-key")

    async def _return_prose(*args, **kwargs):
        return "Sure, here are some skills you might like!"

    monkeypatch.setattr(skills_mod, "openrouter_chat", _return_prose)

    resp = api_client.post("/api/v1/skills/search", json={"goal": "deploy a discord bot"})

    assert resp.status_code == 200
    assert resp.json()["usedFallback"] is True


def test_search_falls_back_on_hallucinated_names(api_client, monkeypatch):
    """Test search falls back when every LLM-returned name is not in the catalog."""
    import json
    from app.core.config import settings
    from app.api.v1.endpoints import skills as skills_mod

    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "test-key")

    async def _return_hallucinated(*args, **kwargs):
        return json.dumps({"matches": [{"name": "not-a-real-skill", "rationale": "made up"}]})

    monkeypatch.setattr(skills_mod, "openrouter_chat", _return_hallucinated)

    resp = api_client.post("/api/v1/skills/search", json={"goal": "deploy a discord bot"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["usedFallback"] is True
    assert all(m["name"] != "not-a-real-skill" for m in body["matches"])


def test_search_returns_llm_matches_on_success(api_client, monkeypatch):
    """Test search returns the LLM's ranked matches when everything succeeds."""
    import json
    from app.core.config import settings
    from app.api.v1.endpoints import skills as skills_mod

    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "test-key")

    async def _return_valid(*args, **kwargs):
        return json.dumps(
            {
                "matches": [
                    {
                        "name": "hypercode-broski-discord-bot",
                        "rationale": "Builds and maintains the BROski Discord bot including moderation commands.",
                    }
                ]
            }
        )

    monkeypatch.setattr(skills_mod, "openrouter_chat", _return_valid)

    resp = api_client.post("/api/v1/skills/search", json={"goal": "deploy a discord bot with moderation"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["usedFallback"] is False
    assert body["error"] is None
    assert body["matches"] == [
        {
            "name": "hypercode-broski-discord-bot",
            "rationale": "Builds and maintains the BROski Discord bot including moderation commands.",
        }
    ]
