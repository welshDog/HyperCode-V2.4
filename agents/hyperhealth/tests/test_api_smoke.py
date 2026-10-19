"""HTTP smoke test for the HyperHealth API.

Pins the observable behaviour of the HTTP layer (auth, validation, status codes, OpenAPI) so a
FastAPI / Starlette upgrade that changes any of it fails here instead of in production.

The database is replaced by a fake async session and the app's lifespan is NOT started (it needs a
real Postgres), so this checks routing, dependency handling and validation only.

Run from the repository root, because the other tests patch ``agents.hyperhealth.worker``:
    PYTHONPATH=. pytest agents/hyperhealth/tests -q
"""
from __future__ import annotations

import importlib
import os
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("API_KEY", "test-key-hyperhealth")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("HEALER_URL", "http://healer:8008")
os.environ.setdefault("ENVIRONMENT", "test")

KEY = {"X-API-Key": "test-key-hyperhealth"}
CHECK_ID = str(uuid.uuid4())


class _EmptyResult:
    """What a query returns when the table is empty."""

    def scalars(self):
        return self

    def all(self):
        return []

    def first(self):
        return None

    def scalar_one_or_none(self):
        return None

    def scalar(self):
        return 0

    def fetchall(self):
        return []

    def __iter__(self):
        return iter([])


async def _fake_db():
    session = MagicMock()
    session.execute = AsyncMock(return_value=_EmptyResult())
    session.get = AsyncMock(return_value=None)
    for name in ("commit", "refresh", "delete", "flush", "rollback"):
        setattr(session, name, AsyncMock())
    session.add = MagicMock()
    yield session


@pytest.fixture(scope="module")
def client():
    main = importlib.import_module("agents.hyperhealth.main")
    main.app.dependency_overrides[main.get_db] = _fake_db
    # No ``with``: entering the context would start the lifespan, which needs a real database.
    yield TestClient(main.app, raise_server_exceptions=False)
    main.app.dependency_overrides.clear()


# (method, path, request kwargs, expected status)
CASES = [
    ("GET", "/health", {}, 200),
    ("GET", "/metrics", {}, 200),
    # Auth: a missing header is a validation error, a wrong key is rejected.
    ("GET", "/checks", {}, 422),
    ("GET", "/checks", {"headers": {"X-API-Key": "nope"}}, 401),
    ("GET", "/checks", {"headers": KEY}, 200),
    # Query / path validation.
    ("GET", "/checks?enabled_only=maybe", {"headers": KEY}, 422),
    ("GET", "/checks/not-a-uuid", {"headers": KEY}, 422),
    ("GET", f"/checks/{CHECK_ID}", {"headers": KEY}, 404),
    ("GET", f"/checks/{CHECK_ID}/results?limit=501", {"headers": KEY}, 422),
    ("GET", f"/checks/{CHECK_ID}/results?limit=10", {"headers": KEY}, 200),
    ("POST", "/checks", {"headers": KEY, "json": {}}, 422),
    ("DELETE", f"/checks/{CHECK_ID}", {"headers": KEY}, 404),
    ("PATCH", f"/checks/{CHECK_ID}", {"headers": KEY, "json": {"enabled": False}}, 404),
    ("GET", "/health/report?env=prod", {"headers": KEY}, 200),
    ("POST", "/selfheal/trigger", {"headers": KEY}, 422),
    # Generated documentation.
    ("GET", "/openapi.json", {}, 200),
    ("GET", "/docs", {}, 200),
]


@pytest.mark.parametrize("method,path,kwargs,expected", CASES, ids=[f"{m} {p}" for m, p, _, _ in CASES])
def test_status_code(client, method, path, kwargs, expected):
    assert client.request(method, path, **kwargs).status_code == expected


def test_metrics_is_prometheus_text(client):
    response = client.get("/metrics")
    assert response.headers["content-type"].startswith("text/plain")
    assert "# HELP" in response.text


def test_openapi_describes_the_service(client):
    spec = client.get("/openapi.json").json()
    assert spec["info"]["title"] == "HyperHealth"
    assert len(spec["paths"]) == 7
    assert "/checks/{check_id}" in spec["paths"]
