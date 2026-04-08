import pytest


def test_redact_secrets_masks_common_tokens():
    from app.core.model_routes import redact_secrets

    sk = "sk-" + "abcdefghijklmnopqrstuvwxyz012345"
    ghp = "ghp_" + "abcdefghijklmnopqrstuvwxyz012345"
    jwt = "eyJ" + "abcdefghijklmno" + "." + "pqrstuvwxyzABCDEFGH" + "." + "ijklmnopQRSTUVWX"
    text = f"{sk} {ghp} {jwt}"
    redacted = redact_secrets(text)
    assert "sk-" not in redacted
    assert "ghp_" not in redacted
    assert "eyJ" not in redacted
    assert "[REDACTED]" in redacted


def test_select_model_route_prefers_healer_for_incident_when_enabled():
    from app.core.model_routes import ModelRouteContext, select_model_route
    from app.core.config import settings

    settings.HEALER_ALPHA_ENABLED = True
    settings.HUNTER_ALPHA_ENABLED = True

    route = select_model_route(ModelRouteContext(kind="incident"), settings)
    assert route is not None
    assert route.name == "healer_alpha"


def test_select_model_route_uses_hunter_for_architecture_when_enabled():
    from app.core.model_routes import ModelRouteContext, select_model_route
    from app.core.config import settings

    settings.HEALER_ALPHA_ENABLED = False
    settings.HUNTER_ALPHA_ENABLED = True

    route = select_model_route(ModelRouteContext(kind="architecture", cross_repo=True), settings)
    assert route is not None
    assert route.name == "hunter_alpha"


@pytest.mark.asyncio
async def test_brain_routes_to_openrouter_when_requested(monkeypatch):
    from app.agents.brain import Brain
    from app.core.config import settings
    import app.core.model_routes as routes_mod

    settings.OLLAMA_HOST = ""
    settings.PERPLEXITY_SESSION_AUTH = False
    settings.PERPLEXITY_API_KEY = None
    settings.OPENROUTER_API_KEY = "k"
    settings.HUNTER_ALPHA_ENABLED = True

    post_capture: dict = {}

    class DummyResponse:
        def __init__(self, status_code: int, json_data: dict):
            self.status_code = status_code
            self._json_data = json_data
            self.text = ""

        def json(self) -> dict:
            return self._json_data

    class CloudClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url: str, json: dict, headers: dict):
            post_capture["url"] = url
            post_capture["json"] = json
            post_capture["headers"] = headers
            return DummyResponse(200, {"choices": [{"message": {"content": "hi"}}]})

    monkeypatch.setattr(routes_mod.httpx, "AsyncClient", lambda *a, **k: CloudClient())

    b = Brain()
    result = await b.think(
        "Role",
        "Plan the next version",
        use_memory=False,
        route_context={"kind": "architecture", "cross_repo": True},
    )
    assert result == "hi"
    assert "/chat/completions" in post_capture["url"]
    assert post_capture["headers"]["Authorization"] == "Bearer k"
