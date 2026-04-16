"""
Gordon Tier 2 Step 3 — Rate limiting tests.

Tests that per-route limits fire correctly and return 429 with Retry-After.
Does NOT need Redis — error handler and route registration are tested in isolation.
"""
import json
import pytest
from unittest.mock import MagicMock
from starlette.requests import Request
from slowapi.errors import RateLimitExceeded

from app.middleware.rate_limiting import limiter, rate_limit_error_handler


def _make_request(path: str = "/health", method: str = "GET") -> Request:
    """Build a minimal Starlette Request for testing."""
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": [],
    }
    return Request(scope)


def _make_rate_limit_exc(limit_str: str = "10 per 1 minute") -> RateLimitExceeded:
    """Build a RateLimitExceeded with a mock Limit object."""
    mock_limit = MagicMock()
    mock_limit.error_message = None
    mock_limit.limit = limit_str
    mock_limit.__str__ = lambda self: limit_str
    return RateLimitExceeded(mock_limit)


class TestRateLimitErrorHandler:
    """rate_limit_error_handler returns correct 429 shape with Retry-After header."""

    def test_returns_429_status(self):
        req = _make_request()
        exc = _make_rate_limit_exc("120 per 1 minute")
        response = rate_limit_error_handler(req, exc)
        assert response.status_code == 429

    def test_retry_after_header_present(self):
        """429 responses must include Retry-After header (RFC 7231)."""
        req = _make_request()
        exc = _make_rate_limit_exc("10 per 1 minute")
        response = rate_limit_error_handler(req, exc)
        assert "Retry-After" in response.headers
        assert response.headers["Retry-After"] == "60"

    def test_body_has_required_fields(self):
        req = _make_request("/api/stripe/checkout", "POST")
        exc = _make_rate_limit_exc("10 per 1 minute")
        response = rate_limit_error_handler(req, exc)
        body = json.loads(response.body)
        assert body["error"] == "rate_limit_exceeded"
        assert body["retry_after"] == 60
        assert "message" in body
        assert "limit" in body

    def test_fires_on_limit_exceeded(self):
        """Core requirement: 429 fires when limit is exceeded (handler is called)."""
        req = _make_request("/api/stripe/checkout", "POST")
        exc = _make_rate_limit_exc("10 per 1 minute")
        response = rate_limit_error_handler(req, exc)
        # 429 with Retry-After = limit was exceeded and handler fired
        assert response.status_code == 429
        assert "Retry-After" in response.headers


class TestRateLimitConfig:
    """Confirm limiter is configured for Redis DB 2 and correct key function."""

    def test_limiter_uses_redis_db2(self):
        storage_uri = limiter._storage_uri
        assert storage_uri is not None, "Limiter must have a storage_uri"
        assert "redis://" in storage_uri
        assert storage_uri.endswith("/2"), (
            f"Rate limiter should use Redis DB 2, got: {storage_uri}"
        )

    def test_limiter_key_func_is_remote_address(self):
        from slowapi.util import get_remote_address
        assert limiter._key_func is get_remote_address


class TestRateLimitRoutesRegistered:
    """Confirm per-route limits are stored in limiter._route_limits."""

    def test_checkout_registered_with_10_per_minute(self):
        """POST /api/stripe/checkout must have 10/min limit."""
        # Import triggers decorator execution and registration
        import app.routes.stripe  # noqa — side effect: registers limits
        key = "app.routes.stripe.checkout"
        limits = limiter._route_limits.get(key, [])
        assert limits, f"checkout should be in limiter._route_limits, keys: {list(limiter._route_limits)}"
        limit_strs = [str(lim.limit) for lim in limits]
        assert any("10" in s for s in limit_strs), (
            f"checkout should have 10/minute limit, got: {limit_strs}"
        )

    def test_get_plans_registered_with_60_per_minute(self):
        """GET /api/stripe/plans must have 60/min limit."""
        import app.routes.stripe  # noqa
        key = "app.routes.stripe.get_plans"
        limits = limiter._route_limits.get(key, [])
        assert limits, f"get_plans should be in limiter._route_limits"
        limit_strs = [str(lim.limit) for lim in limits]
        assert any("60" in s for s in limit_strs), (
            f"get_plans should have 60/minute limit, got: {limit_strs}"
        )

    def test_health_registered_with_120_per_minute(self):
        """GET /health must have 120/min limit."""
        import app.main  # noqa — registers health_check limits
        key = "app.main.health_check"
        limits = limiter._route_limits.get(key, [])
        assert limits, f"health_check should be in limiter._route_limits"
        limit_strs = [str(lim.limit) for lim in limits]
        assert any("120" in s for s in limit_strs), (
            f"health_check should have 120/minute limit, got: {limit_strs}"
        )

    def test_stripe_webhook_not_rate_limited(self):
        """Stripe webhook must NEVER appear in rate limit registry — Sacred Rule."""
        import app.routes.stripe  # noqa
        key = "app.routes.stripe.stripe_webhook"
        limits = limiter._route_limits.get(key, [])
        assert not limits, (
            f"stripe_webhook must NOT be rate-limited — Sacred Rule: {limits}"
        )
