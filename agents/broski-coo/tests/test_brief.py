import json
from unittest.mock import AsyncMock, patch

import pytest


class _MockResponse:
    """Mirrors backend/tests/test_missions_endpoint.py's httpx mock shape."""

    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")

    def json(self):
        return self._payload

    @property
    def text(self):
        return json.dumps(self._payload)


@pytest.fixture(autouse=True)
def _no_llm_keys_and_unreachable_ollama(monkeypatch):
    """Deterministic, network-free default for every test in this file: no
    Anthropic/OpenRouter keys, and an Ollama base URL that fails fast
    (connection refused on localhost) rather than depending on DNS
    resolution of the 'ollama' hostname, which isn't reachable in a bare
    test environment."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("LLM_API_BASE", "http://127.0.0.1:1/v1")


@pytest.mark.asyncio
async def test_health_no_auth_required(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy", "agent": "broski-coo"}


@pytest.mark.asyncio
async def test_brief_503_when_no_key_configured(client, monkeypatch):
    monkeypatch.delenv("HYPERCODE_API_KEY", raising=False)
    monkeypatch.delenv("AGENT_API_KEY", raising=False)
    resp = await client.post("/brief")
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_brief_401_on_missing_key(client, monkeypatch):
    monkeypatch.setenv("HYPERCODE_API_KEY", "secret123")
    resp = await client.post("/brief")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_brief_401_on_wrong_key(client, monkeypatch):
    monkeypatch.setenv("HYPERCODE_API_KEY", "secret123")
    resp = await client.post("/brief", headers={"x-agent-key": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_brief_degrades_when_registry_unreachable(client, monkeypatch, tmp_path):
    monkeypatch.setenv("HYPERCODE_API_KEY", "secret123")
    import main

    monkeypatch.setattr(main, "REPO_ROOT_PATH", str(tmp_path))

    with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=RuntimeError("connection refused"))):
        resp = await client.post("/brief", headers={"x-agent-key": "secret123"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["sources"]["fleet_status"]["status"] == "unavailable"
    assert body["sources"]["whats_done"]["status"] == "unavailable"
    assert body["provider_used"] == "none"
    assert "LLM call failed" in body["brief"]


@pytest.mark.asyncio
async def test_brief_flags_degraded_registry_payload(client, monkeypatch, tmp_path):
    monkeypatch.setenv("HYPERCODE_API_KEY", "secret123")
    import main

    monkeypatch.setattr(main, "REPO_ROOT_PATH", str(tmp_path))

    degraded_payload = {
        "summary": {
            "total": 3,
            "healthy": 0,
            "running": 0,
            "down": 0,
            "not_deployed": 0,
            "crash_looping": 0,
        },
        "agents": [
            {"name": "a", "status": "unknown"},
            {"name": "b", "status": "unknown"},
            {"name": "c", "status": "unknown"},
        ],
    }
    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=_MockResponse(degraded_payload))):
        resp = await client.post("/brief", headers={"x-agent-key": "secret123"})

    assert resp.status_code == 200
    assert resp.json()["sources"]["fleet_status"]["status"] == "degraded"


@pytest.mark.asyncio
async def test_brief_healthy_registry_payload_reports_ok(client, monkeypatch, tmp_path):
    monkeypatch.setenv("HYPERCODE_API_KEY", "secret123")
    import main

    monkeypatch.setattr(main, "REPO_ROOT_PATH", str(tmp_path))

    healthy_payload = {
        "summary": {
            "total": 42,
            "healthy": 35,
            "running": 5,
            "down": 1,
            "not_deployed": 1,
            "crash_looping": 0,
        },
        "agents": [{"name": "a", "status": "healthy"}],
    }
    with patch("httpx.AsyncClient.get", new=AsyncMock(return_value=_MockResponse(healthy_payload))):
        resp = await client.post("/brief", headers={"x-agent-key": "secret123"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["sources"]["fleet_status"]["status"] == "ok"
    assert body["sources"]["fleet_status"]["summary"]["total"] == 42


@pytest.mark.asyncio
async def test_brief_no_llm_keys_falls_through_to_string_never_500s(client, monkeypatch, tmp_path):
    monkeypatch.setenv("HYPERCODE_API_KEY", "secret123")
    import main

    monkeypatch.setattr(main, "REPO_ROOT_PATH", str(tmp_path))

    with patch("httpx.AsyncClient.get", new=AsyncMock(side_effect=RuntimeError("connection refused"))):
        resp = await client.post("/brief", headers={"x-agent-key": "secret123"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["provider_used"] == "none"
    assert isinstance(body["brief"], str) and body["brief"]


@pytest.mark.asyncio
async def test_openrouter_preset_call_uses_preset_model_field(monkeypatch):
    """The request must reference the preset (@preset/<slug>), not a locally
    chosen model -- OpenRouter's own preset owns model selection, fallback
    ordering, max_price, and data_collection policy server-side."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-or-key")
    monkeypatch.setenv("OPENROUTER_PRESET", "free-router")
    import main

    real_content_payload = {
        "model": "z-ai/glm-5.2:free",
        "choices": [{"message": {"content": "a real brief"}}],
    }
    captured_payload = {}

    async def _fake_post(self, url, json=None, headers=None, timeout=None):
        captured_payload.update(json or {})
        return _MockResponse(real_content_payload)

    with patch("httpx.AsyncClient.post", new=_fake_post):
        text, model = await main._openrouter_chat_preset("sys", "user", 900)

    assert text == "a real brief"
    assert model == "z-ai/glm-5.2:free"  # whatever the preset actually routed to
    assert captured_payload["model"] == "@preset/free-router"


@pytest.mark.asyncio
async def test_openrouter_null_content_raises(monkeypatch):
    """Regression test for a real bug caught live: a reasoning-capable free
    model (stealth/ox-alpha, confirmed against the real OpenRouter API,
    reached through this exact preset) can return HTTP 200 with
    message.content == null when finish_reason is "length" -- the token
    budget was spent on internal reasoning before any output text was
    emitted. A 200 must not be treated as usable content."""
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-or-key")
    import main

    null_content_payload = {"model": "stealth/ox-alpha", "choices": [{"message": {"content": None}}]}

    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=_MockResponse(null_content_payload))):
        with pytest.raises(RuntimeError, match="empty/null content"):
            await main._openrouter_chat_preset("sys", "user", 900)


@pytest.mark.asyncio
async def test_openrouter_non_200_raises(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-or-key")
    import main

    with patch(
        "httpx.AsyncClient.post",
        new=AsyncMock(return_value=_MockResponse({"error": "bad preset"}, status_code=404)),
    ):
        with pytest.raises(RuntimeError, match="404"):
            await main._openrouter_chat_preset("sys", "user", 900)


def test_newest_handover_picks_correct_file(monkeypatch, tmp_path):
    import main

    (tmp_path / "NEXT_SESSION_HANDOVER_2026-08-20-evening.md").write_text(
        "older, same-date evening", encoding="utf-8"
    )
    (tmp_path / "NEXT_SESSION_HANDOVER_2026-08-20-late-night.md").write_text(
        "newer, same-date late-night", encoding="utf-8"
    )
    (tmp_path / "NEXT_SESSION_HANDOVER_2026-08-19.md").write_text("oldest", encoding="utf-8")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "NEXT_SESSION_HANDOVER_2026-08-21-late-night.md").write_text(
        "newest overall, in docs/", encoding="utf-8"
    )

    monkeypatch.setattr(main, "REPO_ROOT_PATH", str(tmp_path))
    result = main._newest_handover()

    assert result["status"] == "ok"
    assert result["path"] == "NEXT_SESSION_HANDOVER_2026-08-21-late-night.md"
    assert "newest overall" in result["excerpt"]


def test_newest_handover_unavailable_when_none_found(monkeypatch, tmp_path):
    import main

    monkeypatch.setattr(main, "REPO_ROOT_PATH", str(tmp_path))
    result = main._newest_handover()
    assert result["status"] == "unavailable"


def test_whats_done_excerpt_is_bounded_to_latest_entry(monkeypatch, tmp_path):
    import main

    # Mirrors the real WHATS_DONE.md shape: header, then a divider, then the
    # most recent entry, then a divider, then older entries -- two dividers
    # minimum, not one. The excerpt should stop at the SECOND divider (end
    # of the first/most-recent entry), keeping the header + Entry 1.
    content = (
        "# WHATS_DONE\n\n> header line\n\n---\n\n"
        "## Entry 1\nfirst entry text\n\n---\n\n"
        "## Entry 2\nsecond entry text\n"
    )
    (tmp_path / "WHATS_DONE.md").write_text(content, encoding="utf-8")
    monkeypatch.setattr(main, "REPO_ROOT_PATH", str(tmp_path))

    result = main._read_whats_done()

    assert result["status"] == "ok"
    assert "Entry 1" in result["excerpt"]
    assert "Entry 2" not in result["excerpt"]


def test_whats_done_unavailable_when_missing(monkeypatch, tmp_path):
    import main

    monkeypatch.setattr(main, "REPO_ROOT_PATH", str(tmp_path))
    result = main._read_whats_done()
    assert result["status"] == "unavailable"
