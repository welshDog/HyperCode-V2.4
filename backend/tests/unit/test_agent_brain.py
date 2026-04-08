import pytest


class _DummyResponse:
    def __init__(self, status_code: int, json_data: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text

    def json(self) -> dict:
        return self._json_data


class _DummyAsyncClient:
    def __init__(self, *, post_response: _DummyResponse, post_capture: dict, timeout: float | None = None):
        self._post_response = post_response
        self._post_capture = post_capture
        self._timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url: str, json: dict, headers: dict | None = None):
        self._post_capture["url"] = url
        self._post_capture["json"] = json
        return self._post_response


@pytest.mark.asyncio
async def test_recall_context_returns_rag_results(monkeypatch):
    from app.agents.brain import Brain
    from app.core.rag import rag

    async_brain = Brain()

    def fake_query(query_text: str, n_results: int = 5, filters=None):
        return ["doc-a", "doc-b"]

    monkeypatch.setattr(rag, "query", fake_query)

    result = await async_brain.recall_context(query="hello", limit=2)
    assert "--- Semantic Memory (RAG) ---" in result
    assert "doc-a" in result
    assert "doc-b" in result


@pytest.mark.asyncio
async def test_recall_context_falls_back_to_storage_on_rag_failure(monkeypatch):
    from app.agents.brain import Brain
    from app.core.rag import rag
    from app.core.config import settings
    import app.core.storage as storage_mod

    async_brain = Brain()

    def fake_query(query_text: str, n_results: int = 5, filters=None):
        raise RuntimeError("rag down")

    class DummyStorage:
        def list_files(self, limit: int = 10):
            return ["x.md"]

        def get_file_content(self, key: str) -> str:
            return "hello world"

    monkeypatch.setattr(rag, "query", fake_query)
    monkeypatch.setattr(settings, "BRAIN_ALLOW_FILE_FALLBACK", True)
    monkeypatch.setattr(storage_mod, "get_storage", lambda: DummyStorage())

    result = await async_brain.recall_context(query="hello", limit=1)
    assert "Recent File: x.md" in result
    assert "hello world" in result


@pytest.mark.asyncio
async def test_think_local_llm_success_with_auto_model(monkeypatch):
    import app.agents.brain as brain_mod
    from app.agents.brain import Brain
    from app.core.config import settings

    settings.OLLAMA_HOST = "http://ollama"
    settings.DEFAULT_LLM_MODEL = "auto"

    async_brain = Brain()

    async def fake_resolve(client):
        return "tinyllama"

    async_brain._ollama_model_resolver.resolve = fake_resolve

    post_capture: dict = {}

    def client_factory(*args, **kwargs):
        return _DummyAsyncClient(
            post_response=_DummyResponse(200, {"response": "ok"}),
            post_capture=post_capture,
            timeout=kwargs.get("timeout"),
        )

    monkeypatch.setattr(brain_mod.httpx, "AsyncClient", client_factory)

    result = await async_brain.think("Role", "Do the thing", use_memory=False)
    assert result == "ok"
    assert post_capture["url"] == "http://ollama/api/generate"
    assert post_capture["json"]["model"] == "tinyllama"
    assert post_capture["json"]["stream"] is False
    assert "options" in post_capture["json"]


@pytest.mark.asyncio
async def test_think_local_llm_non_200_falls_back_to_session(monkeypatch):
    import app.agents.brain as brain_mod
    from app.agents.brain import Brain
    from app.core.config import settings

    settings.OLLAMA_HOST = "http://ollama"
    settings.DEFAULT_LLM_MODEL = "tinyllama"
    settings.PERPLEXITY_SESSION_AUTH = True

    async_brain = Brain()
    post_capture: dict = {}

    def client_factory(*args, **kwargs):
        return _DummyAsyncClient(
            post_response=_DummyResponse(500, {}, "nope"),
            post_capture=post_capture,
            timeout=kwargs.get("timeout"),
        )

    monkeypatch.setattr(brain_mod.httpx, "AsyncClient", client_factory)

    result = await async_brain.think("Role", "Do the thing", use_memory=False)
    assert result == "Perplexity Session Auth is active. (Simulated Response)"


@pytest.mark.asyncio
async def test_think_returns_error_when_no_llm_available(monkeypatch):
    from app.agents.brain import Brain
    from app.core.config import settings

    settings.OLLAMA_HOST = ""
    settings.PERPLEXITY_SESSION_AUTH = False
    settings.PERPLEXITY_API_KEY = None

    async_brain = Brain()
    result = await async_brain.think("Role", "Do the thing", use_memory=False)
    assert "No valid LLM provider available" in result


@pytest.mark.asyncio
async def test_think_cloud_api_success(monkeypatch):
    """
    FIX: brain.py now validates PERPLEXITY_API_KEY starts with 'pplx-' before
    routing to the cloud provider. Old mock used key='k' which failed validation
    and returned 'No valid LLM provider' before ever reaching the mock.
    Fix: use a valid pplx- prefixed key + mock at the provider selection level.
    """
    import app.agents.brain as brain_mod
    from app.agents.brain import Brain
    from app.core.config import settings

    settings.OLLAMA_HOST = ""
    settings.PERPLEXITY_SESSION_AUTH = False
    settings.PERPLEXITY_API_KEY = "pplx-" + "x" * 20

    async_brain = Brain()
    post_capture: dict = {}

    class CloudClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url: str, json: dict, headers: dict | None = None):
            post_capture["url"] = url
            post_capture["json"] = json
            return _DummyResponse(200, {"choices": [{"message": {"content": "hi"}}]})

    monkeypatch.setattr(brain_mod.httpx, "AsyncClient", lambda *a, **k: CloudClient())

    result = await async_brain.think("Role", "Do the thing", use_memory=False)
    assert result == "hi"
    assert "openrouter" in post_capture.get("url", "") or "perplexity" in post_capture.get("url", "")


@pytest.mark.asyncio
async def test_think_cloud_api_non_200_returns_error(monkeypatch):
    """
    FIX: Same root cause as test_think_cloud_api_success.
    Key must be 'pplx-' prefixed to reach the cloud API path.
    """
    import app.agents.brain as brain_mod
    from app.agents.brain import Brain
    from app.core.config import settings

    settings.OLLAMA_HOST = ""
    settings.PERPLEXITY_SESSION_AUTH = False
    settings.PERPLEXITY_API_KEY = "pplx-" + "x" * 20

    async_brain = Brain()

    class CloudClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url: str, json: dict, headers: dict | None = None):
            return _DummyResponse(500, {}, "bad")

    monkeypatch.setattr(brain_mod.httpx, "AsyncClient", lambda *a, **k: CloudClient())

    result = await async_brain.think("Role", "Do the thing", use_memory=False)
    # Brain falls back on non-200 responses — no other providers configured so reaches terminal error
    assert "No valid LLM provider available" in result

