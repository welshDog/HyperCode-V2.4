"""
Phase 10D — Agent API key auth + rate limiting tests.
All DB and Redis calls are mocked.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.middleware.agent_auth import generate_agent_key, hash_agent_key


# ── Unit: key generation ──────────────────────────────────────────────────────

def test_generate_agent_key_format():
    key = generate_agent_key()
    assert key.startswith("hc_")
    # token_urlsafe(32) → 43 chars; + "hc_" prefix → 46 total
    assert len(key) == 46


def test_hash_agent_key_deterministic():
    key = generate_agent_key()
    assert hash_agent_key(key) == hash_agent_key(key)


def test_hash_agent_key_different_keys():
    assert hash_agent_key(generate_agent_key()) != hash_agent_key(generate_agent_key())


def test_hash_is_hex_64():
    h = hash_agent_key("hc_test")
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _mock_db_found(agent_name="healer-agent", rpm=200):
    """AsyncSessionLocal mock that returns one row."""
    mock_row = MagicMock()
    mock_row.mappings.return_value.first.return_value = {
        "agent_name": agent_name,
        "rate_limit_rpm": rpm,
    }
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_row)
    mock_db.commit = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    return mock_db


def _mock_db_not_found():
    """AsyncSessionLocal mock that returns no row (invalid key)."""
    mock_row = MagicMock()
    mock_row.mappings.return_value.first.return_value = None
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_row)
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    return mock_db


# ── Integration: admin CRUD endpoints ────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_agent_keys_requires_superuser():
    """GET /api/v1/agent-keys must be 401/403 without auth."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/agent-keys")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_agent_key_requires_superuser():
    """POST /api/v1/agent-keys must be 401/403 without auth."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/v1/agent-keys", json={"agent_name": "test-agent"})
    assert resp.status_code in (401, 403)


# ── Integration: middleware bypass ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_accessible_without_agent_key():
    """GET /health needs no auth — rate limit bypass unrelated."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_plans_endpoint_no_agent_key_needed():
    """GET /api/stripe/plans is a public endpoint — no agent key required."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/stripe/plans")
    assert resp.status_code == 200


# ── Unit: get_agent_from_key dependency ──────────────────────────────────────

@pytest.mark.asyncio
async def test_get_agent_from_key_valid():
    """Valid key returns agent dict."""
    from app.middleware.agent_auth import get_agent_from_key

    raw_key = generate_agent_key()
    mock_db = _mock_db_found()

    with patch("app.middleware.agent_auth.AsyncSessionLocal", return_value=mock_db), \
         patch("app.middleware.agent_auth._check_agent_rate_limit", return_value=True):
        from starlette.requests import Request as StarletteRequest
        from starlette.datastructures import Headers
        scope = {"type": "http", "method": "GET", "path": "/", "query_string": b"", "headers": []}
        mock_request = MagicMock(spec=StarletteRequest)
        result = await get_agent_from_key(request=mock_request, x_agent_key=raw_key)

    assert result is not None
    assert result["agent_name"] == "healer-agent"


@pytest.mark.asyncio
async def test_get_agent_from_key_absent_returns_none():
    """No header → None (optional auth)."""
    from app.middleware.agent_auth import get_agent_from_key
    from starlette.requests import Request as StarletteRequest
    mock_request = MagicMock(spec=StarletteRequest)
    result = await get_agent_from_key(request=mock_request, x_agent_key=None)
    assert result is None


@pytest.mark.asyncio
async def test_get_agent_from_key_invalid_raises_403():
    """Invalid key → 403."""
    from app.middleware.agent_auth import get_agent_from_key
    from fastapi import HTTPException
    from starlette.requests import Request as StarletteRequest

    mock_db = _mock_db_not_found()
    mock_request = MagicMock(spec=StarletteRequest)

    with patch("app.middleware.agent_auth.AsyncSessionLocal", return_value=mock_db):
        with pytest.raises(HTTPException) as exc_info:
            await get_agent_from_key(request=mock_request, x_agent_key="hc_invalid_key_xyz")

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_agent_from_key_rate_limited_raises_429():
    """Valid key but rate limit hit → 429."""
    from app.middleware.agent_auth import get_agent_from_key
    from fastapi import HTTPException
    from starlette.requests import Request as StarletteRequest

    raw_key = generate_agent_key()
    mock_db = _mock_db_found()
    mock_request = MagicMock(spec=StarletteRequest)

    with patch("app.middleware.agent_auth.AsyncSessionLocal", return_value=mock_db), \
         patch("app.middleware.agent_auth._check_agent_rate_limit", return_value=False):
        with pytest.raises(HTTPException) as exc_info:
            await get_agent_from_key(request=mock_request, x_agent_key=raw_key)

    assert exc_info.value.status_code == 429


# ── Unit: require_agent_key ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_require_agent_key_raises_401_when_none():
    """No agent → 401 from strict dependency."""
    from app.middleware.agent_auth import require_agent_key
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        await require_agent_key(agent=None)

    assert exc_info.value.status_code == 401
