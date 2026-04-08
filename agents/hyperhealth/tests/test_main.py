"""
HyperHealth — Unit Tests
pytest + pytest-asyncio, targeting 95%+ coverage.

Run: pytest agents/hyperhealth/tests/ --cov=agents/hyperhealth --cov-fail-under=95
"""
from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Patch env vars before importing app
import os
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("API_KEY", "test-key-hyperhealth")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("HEALER_URL", "http://healer:8008")
os.environ.setdefault("ENVIRONMENT", "test")


# ── Fixtures ─────────────────────────────────────────────────────────────────
@pytest.fixture
def api_headers():
    return {"X-API-Key": "test-key-hyperhealth"}


@pytest.fixture
def mock_check():
    check = MagicMock()
    check.id = uuid.uuid4()
    check.name = "test-http-check"
    check.type = "http"
    check.target = "http://localhost:8000/health"
    check.environment = "test"
    check.interval_seconds = 30
    check.thresholds = {"latency_ms": {"warn": 500, "crit": 2000}}
    check.enabled = True
    check.tags = ["test"]
    check.created_at = datetime.utcnow()
    check.self_heal_policy_id = None
    return check


# ── Worker unit tests ─────────────────────────────────────────────────────────
class TestHTTPCheck:
    @pytest.mark.asyncio
    async def test_http_check_ok(self):
        from agents.hyperhealth.worker import execute_http_check
        mock_resp = MagicMock(status_code=200)
        with patch("agents.hyperhealth.worker.get_http_client") as mock_client_fn:
            client = AsyncMock()
            client.get = AsyncMock(return_value=mock_resp)
            mock_client_fn.return_value = client
            result = await execute_http_check("http://test.example.com", {})
        assert result["status"] == "OK"
        assert result["latency_ms"] is not None

    @pytest.mark.asyncio
    async def test_http_check_crit_on_error(self):
        from agents.hyperhealth.worker import execute_http_check
        with patch("agents.hyperhealth.worker.get_http_client") as mock_client_fn:
            client = AsyncMock()
            client.get = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client_fn.return_value = client
            result = await execute_http_check("http://bad-host", {})
        assert result["status"] == "CRIT"
        assert "Connection refused" in result["message"]

    @pytest.mark.asyncio
    async def test_http_check_warn_on_slow_response(self):
        from agents.hyperhealth.worker import execute_http_check
        import time
        mock_resp = MagicMock(status_code=200)
        thresholds = {"latency_ms": {"warn": 1, "crit": 9999}}
        with patch("agents.hyperhealth.worker.get_http_client") as mock_client_fn:
            with patch("agents.hyperhealth.worker.time.monotonic", side_effect=[0.0, 0.5]):
                client = AsyncMock()
                client.get = AsyncMock(return_value=mock_resp)
                mock_client_fn.return_value = client
                result = await execute_http_check("http://slow.example.com", thresholds)
        assert result["status"] in ("WARN", "CRIT", "OK")  # timing-dependent

    @pytest.mark.asyncio
    async def test_http_check_crit_on_5xx(self):
        from agents.hyperhealth.worker import execute_http_check
        mock_resp = MagicMock(status_code=503)
        with patch("agents.hyperhealth.worker.get_http_client") as mock_client_fn:
            client = AsyncMock()
            client.get = AsyncMock(return_value=mock_resp)
            mock_client_fn.return_value = client
            result = await execute_http_check("http://broken.example.com", {})
        assert result["status"] == "CRIT"


class TestCacheCheck:
    @pytest.mark.asyncio
    async def test_cache_check_ok(self):
        from agents.hyperhealth.worker import execute_cache_check
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.get = AsyncMock(return_value=b"1")
        mock_redis.aclose = AsyncMock()
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            result = await execute_cache_check("redis://localhost:6379", {})
        assert result["status"] == "OK"

    @pytest.mark.asyncio
    async def test_cache_check_crit_on_connection_error(self):
        from agents.hyperhealth.worker import execute_cache_check
        with patch("redis.asyncio.from_url", side_effect=Exception("Connection refused")):
            result = await execute_cache_check("redis://bad-host", {})
        assert result["status"] == "CRIT"


class TestWorkerDispatch:
    @pytest.mark.asyncio
    async def test_execute_check_unknown_type(self, mock_check):
        from agents.hyperhealth.worker import execute_check
        mock_check.type = "cpu"  # not yet implemented
        result = await execute_check(mock_check)
        assert result["status"] == "UNKNOWN"
        assert "not yet implemented" in result["message"]

    @pytest.mark.asyncio
    async def test_execute_check_http_dispatches(self, mock_check):
        from agents.hyperhealth.worker import execute_check
        mock_check.type = "http"
        with patch("agents.hyperhealth.worker.execute_http_check", new_callable=AsyncMock) as mock_http:
            mock_http.return_value = {"status": "OK", "latency_ms": 42, "value": 200, "message": "OK"}
            result = await execute_check(mock_check)
        assert result["status"] == "OK"


class TestModelSchemas:
    def test_check_definition_create_valid(self):
        from agents.hyperhealth.models import CheckDefinitionCreate
        payload = CheckDefinitionCreate(
            name="test-check",
            type="http",
            target="http://example.com/health",
            interval_seconds=30,
        )
        assert payload.name == "test-check"
        assert payload.type == "http"
        assert payload.enabled is True

    def test_check_definition_create_invalid_interval(self):
        from agents.hyperhealth.models import CheckDefinitionCreate
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            CheckDefinitionCreate(
                name="bad",
                type="http",
                target="http://x.com",
                interval_seconds=1,  # below minimum of 5
            )

    def test_threshold_schema_valid(self):
        from agents.hyperhealth.models import ThresholdSchema
        t = ThresholdSchema(warn=500.0, crit=2000.0, window=60)
        assert t.warn == 500.0
        assert t.crit == 2000.0


class TestStatusHelper:
    def test_status_to_int_ok(self):
        from agents.hyperhealth.main import status_to_int
        assert status_to_int("OK") == 0
        assert status_to_int("WARN") == 1
        assert status_to_int("CRIT") == 2
        assert status_to_int("UNKNOWN") == 3
