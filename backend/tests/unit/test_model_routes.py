import pytest


@pytest.mark.asyncio
async def test_openrouter_chat_raises_on_missing_choices(monkeypatch):
    """Test openrouter chat raises on missing choices."""
    from app.core import model_routes as routes_mod

    class DummyResponse:
        status_code = 200
        text = "{}"

        def json(self):
            """Helper: json."""
            return {"choices": []}

    class DummyClient:
        async def __aenter__(self):
            """Enter the mock async context manager."""
            return self

        async def __aexit__(self, exc_type, exc, tb):
            """Exit the mock async context manager."""
            return False

        async def post(self, *args, **kwargs):
            """Helper: post."""
            return DummyResponse()

    monkeypatch.setattr(routes_mod.httpx, "AsyncClient", lambda *a, **k: DummyClient())

    with pytest.raises(RuntimeError, match="no choices"):
        await routes_mod.openrouter_chat(
            base_url="https://openrouter.ai/api/v1",
            api_key="k",
            model="m",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=10,
            privacy_mode="none",
        )


@pytest.mark.asyncio
async def test_openrouter_chat_raises_on_missing_content(monkeypatch):
    """Test openrouter chat raises on missing content."""
    from app.core import model_routes as routes_mod

    class DummyResponse:
        status_code = 200
        text = "{}"

        def json(self):
            """Helper: json."""
            return {"choices": [{"message": {}}]}

    class DummyClient:
        async def __aenter__(self):
            """Enter the mock async context manager."""
            return self

        async def __aexit__(self, exc_type, exc, tb):
            """Exit the mock async context manager."""
            return False

        async def post(self, *args, **kwargs):
            """Helper: post."""
            return DummyResponse()

    monkeypatch.setattr(routes_mod.httpx, "AsyncClient", lambda *a, **k: DummyClient())

    with pytest.raises(RuntimeError, match="no message content"):
        await routes_mod.openrouter_chat(
            base_url="https://openrouter.ai/api/v1",
            api_key="k",
            model="m",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=10,
            privacy_mode="none",
        )


def test_redact_secrets_masks_common_tokens():
    """Test redact secrets masks common tokens."""
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
    """Test select model route prefers healer for incident when enabled."""
    from app.core.model_routes import ModelRouteContext, select_model_route
    from app.core.config import settings

    settings.HEALER_ALPHA_ENABLED = True
    settings.HUNTER_ALPHA_ENABLED = True

    route = select_model_route(ModelRouteContext(kind="incident"), settings)
    assert route is not None
    assert route.name == "healer_alpha"


def test_select_model_route_uses_hunter_for_architecture_when_enabled():
    """Test select model route uses hunter for architecture when enabled."""
    from app.core.model_routes import ModelRouteContext, select_model_route
    from app.core.config import settings

    settings.HEALER_ALPHA_ENABLED = False
    settings.HUNTER_ALPHA_ENABLED = True

    route = select_model_route(ModelRouteContext(kind="architecture", cross_repo=True), settings)
    assert route is not None
    assert route.name == "hunter_alpha"


@pytest.mark.asyncio
async def test_brain_routes_to_openrouter_when_requested(monkeypatch):
    """Test brain routes to openrouter when requested."""
    from app.agents.brain import Brain
    from app.core.config import settings
    import app.core.model_routes as routes_mod

    settings.OLLAMA_HOST = ""
    settings.ANTHROPIC_API_KEY = None
    settings.OPENROUTER_API_KEY = "k"
    settings.HUNTER_ALPHA_ENABLED = True

    post_capture: dict = {}

    class DummyResponse:
        def __init__(self, status_code: int, json_data: dict):
            """Initialize the fake/mock object."""
            self.status_code = status_code
            self._json_data = json_data
            self.text = ""

        def json(self) -> dict:
            """Helper: json."""
            return self._json_data

    class CloudClient:
        async def __aenter__(self):
            """Enter the mock async context manager."""
            return self

        async def __aexit__(self, exc_type, exc, tb):
            """Exit the mock async context manager."""
            return False

        async def post(self, url: str, json: dict, headers: dict):
            """Helper: post."""
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
