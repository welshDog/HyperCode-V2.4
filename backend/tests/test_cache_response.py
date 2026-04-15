"""
Tests for @cache_response decorator — Gordon Tier 2 Step 2.

Uses an in-memory fake cache so no Redis connection is required.
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── Fake in-memory MultiTierCache ────────────────────────────────────────────

class _FakeCache:
    """In-process dict cache — mimics MultiTierCache get/set interface."""

    def __init__(self):
        self._store: dict = {}
        self.hits = 0
        self.misses = 0

    async def get(self, namespace: str, key: str, default=None):
        full = f"{namespace}:{key}"
        if full in self._store:
            self.hits += 1
            return self._store[full]
        self.misses += 1
        return default

    async def set(self, namespace: str, key: str, value, ttl: int = 60):
        self._store[f"{namespace}:{key}"] = value


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def fake_cache():
    return _FakeCache()


@pytest.fixture()
def patched_cache(fake_cache):
    """Patch get_cache() in multi_tier so all cache_response calls use fake."""
    async def _get():
        return fake_cache

    with patch("app.cache.multi_tier.get_cache", side_effect=_get):
        yield fake_cache


# ── GET /api/stripe/plans (TTL 60s) ──────────────────────────────────────────

class TestStripePlansCache:
    def test_plans_first_call_returns_data(self, client, patched_cache):
        """First call: cache miss → real function → populates cache."""
        resp = client.get("/api/stripe/plans")
        assert resp.status_code == 200
        data = resp.json()
        assert "plans" in data
        assert len(data["plans"]) == 7  # 7 price keys

    def test_plans_second_call_hits_cache(self, client, patched_cache):
        """Second call returns same data from cache; hit count increments."""
        r1 = client.get("/api/stripe/plans")
        r2 = client.get("/api/stripe/plans")
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json() == r2.json()
        # First call = miss, second = hit
        assert patched_cache.hits >= 1
        assert patched_cache.misses >= 1

    def test_plans_cache_survives_redis_down(self, client):
        """If Redis/get_cache raises, endpoint still returns data (graceful fallback)."""
        async def _broken():
            raise ConnectionError("Redis gone")

        with patch("app.cache.multi_tier.get_cache", side_effect=_broken):
            resp = client.get("/api/stripe/plans")
        assert resp.status_code == 200
        assert "plans" in resp.json()


# ── GET /health (TTL 10s) ─────────────────────────────────────────────────────

class TestHealthCache:
    def test_health_returns_required_fields(self, client, patched_cache):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        for field in ("status", "service", "version", "environment"):
            assert field in data, f"Missing field: {field}"

    def test_health_second_call_hits_cache(self, client, patched_cache):
        r1 = client.get("/health")
        r2 = client.get("/health")
        assert r1.json() == r2.json()
        assert patched_cache.hits >= 1

    def test_health_cache_fallback_on_error(self, client):
        """Cache errors must never break /health."""
        async def _broken():
            raise RuntimeError("cache exploded")

        with patch("app.cache.multi_tier.get_cache", side_effect=_broken):
            resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


# ── cache_response decorator unit tests ──────────────────────────────────────

class TestCacheResponseDecorator:
    """Test the decorator directly, not through HTTP."""

    @pytest.mark.asyncio
    async def test_calls_through_on_miss(self, fake_cache):
        from app.cache.multi_tier import cache_response

        call_count = 0

        async def _get_fake_cache():
            return fake_cache

        with patch("app.cache.multi_tier.get_cache", side_effect=_get_fake_cache):
            @cache_response("test_ns", ttl=5)
            async def my_endpoint():
                nonlocal call_count
                call_count += 1
                return {"value": 42}

            result1 = await my_endpoint()
            result2 = await my_endpoint()

        assert result1 == {"value": 42}
        assert result2 == {"value": 42}
        assert call_count == 1          # real function called once
        assert fake_cache.hits == 1     # second call was a cache hit
        assert fake_cache.misses == 1   # first call was a miss

    @pytest.mark.asyncio
    async def test_key_includes_primitive_kwargs(self, fake_cache):
        from app.cache.multi_tier import cache_response

        results = []

        async def _get_fake_cache():
            return fake_cache

        with patch("app.cache.multi_tier.get_cache", side_effect=_get_fake_cache):
            @cache_response("test_kw", ttl=5)
            async def endpoint_with_args(limit: int = 10):
                results.append(limit)
                return {"limit": limit}

            await endpoint_with_args(limit=10)
            await endpoint_with_args(limit=10)   # same key → cache hit
            await endpoint_with_args(limit=20)   # different key → miss

        assert results == [10, 20]              # called twice, not three times
        assert fake_cache.hits == 1
        assert fake_cache.misses == 2
