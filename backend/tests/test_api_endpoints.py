"""Unit tests for core API endpoints."""

import pytest
from fastapi import status
from app.core.config import settings


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check_success(self, client):
        """Test health check returns 200."""
        response = client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] in {"ok", "healthy"}

    def test_health_check_response_structure(self, client):
        """Test health check response has required fields."""
        response = client.get("/health")
        data = response.json()

        required_fields = ["status", "service", "version", "environment"]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"


class TestAPIEndpoints:
    """Tests for core API endpoints."""

    def test_root_redirect(self, client):
        """Test root endpoint returns a welcome payload."""
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.json()

    def test_api_docs_accessible(self, client):
        """Test API documentation is accessible."""
        response = client.get(f"{settings.API_V1_STR}/docs")
        assert response.status_code == status.HTTP_200_OK
        assert "swagger" in response.text.lower()

    def test_openapi_schema_accessible(self, client):
        """Test OpenAPI schema is accessible."""
        response = client.get("/openapi.json")
        assert response.status_code == status.HTTP_200_OK
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema


class TestErrorHandling:
    """Tests for error handling."""

    def test_404_not_found(self, client):
        """Test 404 error for non-existent endpoint."""
        response = client.get("/api/nonexistent")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_405_method_not_allowed(self, client):
        """Test 405 error for incorrect HTTP method."""
        response = client.post("/health")
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_422_validation_error(self, client):
        """Test 422 error for invalid request body."""
        response = client.post(
            f"{settings.API_V1_STR}/auth/login/access-token",
            json={"invalid": "data"}
        )
        assert response.status_code == 422


class TestCORSHeaders:
    """Tests for CORS configuration."""

    def test_cors_headers_present(self, client):
        """Test CORS headers are included in responses."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:8088",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access-control-allow-origin" in {k.lower() for k in response.headers.keys()}


class TestRateLimiting:
    """Tests for rate limiting on /api/v1/hypersync/handoff (10 req/min per IP)."""

    def test_rate_limit_exceeded(self, client, monkeypatch):
        from unittest.mock import patch

        from app.core.config import settings as app_settings

        class _FakeRedis:
            def __init__(self):
                self._counters = {}

            async def incr(self, key):
                self._counters[key] = self._counters.get(key, 0) + 1
                return self._counters[key]

            async def expire(self, key, seconds):
                return True

            async def get(self, key):
                return None

            async def set(self, key, value, ex=None, nx=False):
                return True

            async def delete(self, key):
                return 1

            async def aclose(self):
                return None

        fake_redis = _FakeRedis()
        monkeypatch.setattr(app_settings, "HYPERSYNC_MASTER_KEY", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")

        with patch("app.api.v1.endpoints.hypersync.aioredis.from_url", return_value=fake_redis):
            last = None
            for _ in range(11):
                last = client.post(
                    f"{settings.API_V1_STR}/hypersync/handoff",
                    json={"client_id": "client-abc-123", "messages": []},
                )
            assert last is not None
            assert last.status_code == status.HTTP_429_TOO_MANY_REQUESTS


@pytest.mark.parametrize("endpoint", [
    "/health",
    f"{settings.API_V1_STR}/docs",
    "/openapi.json",
])
def test_public_endpoints_accessible(client, endpoint):
    """Test that public endpoints are accessible."""
    response = client.get(endpoint)
    assert response.status_code in [
        status.HTTP_200_OK,
        status.HTTP_307_TEMPORARY_REDIRECT
    ]
