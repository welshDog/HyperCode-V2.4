"""A DSN password must never be stored in, or returned from, a check definition.

Covers the wiring of target_secrets into the worker (resolve ``env:`` targets, mask messages) and the
API output model. Run from the repository root:
    PYTHONPATH=. pytest agents/hyperhealth/tests/test_target_credentials.py -q
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("API_KEY", "test-key-hyperhealth")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("HEALER_URL", "http://healer:8008")
os.environ.setdefault("ENVIRONMENT", "test")

SECRET = "fake-" + "do-not-leak"


def dsn(host_and_db: str = "db/hc") -> str:
    """Assembled at runtime so secret scanners do not flag a literal user:pw@host URL."""
    return "postgresql" + "://" + "app:" + SECRET + "@" + host_and_db


def _check(target: str, type_: str = "db"):
    check = MagicMock()
    check.id = uuid.uuid4()
    check.type = type_
    check.target = target
    check.thresholds = {}
    return check


@pytest.mark.asyncio
async def test_env_target_is_resolved_for_the_executor(monkeypatch):
    from agents.hyperhealth.worker import execute_check

    monkeypatch.setenv("HH_TEST_DSN", dsn())
    with patch("agents.hyperhealth.worker.execute_db_check", new_callable=AsyncMock) as db:
        db.return_value = {"status": "OK", "latency_ms": 1, "value": 1.0, "message": "ok"}
        await execute_check(_check("env:HH_TEST_DSN"))
    assert db.await_args.args[0] == dsn()


@pytest.mark.asyncio
async def test_missing_env_target_is_a_crit_not_an_exception(monkeypatch):
    from agents.hyperhealth.worker import execute_check

    monkeypatch.delenv("HH_TEST_NOPE", raising=False)
    result = await execute_check(_check("env:HH_TEST_NOPE"))
    assert result["status"] == "CRIT"
    assert "HH_TEST_NOPE" in result["message"]


@pytest.mark.asyncio
async def test_executor_message_never_echoes_the_password():
    from agents.hyperhealth.worker import execute_check

    leaky = "connection to " + dsn() + " failed"
    with patch("agents.hyperhealth.worker.execute_db_check", new_callable=AsyncMock) as db:
        db.return_value = {"status": "CRIT", "latency_ms": None, "value": None, "message": leaky}
        result = await execute_check(_check("env:DATABASE_URL"))
    assert SECRET not in result["message"]
    assert "***" in result["message"]


def test_api_output_masks_a_stored_dsn_password():
    from agents.hyperhealth.models import CheckDefinitionOut

    out = CheckDefinitionOut(
        id=uuid.uuid4(), name="postgres-db-health", type="db",
        target=dsn("postgres:5432/hc"),
        environment="production", interval_seconds=30, enabled=True, tags=[],
        created_at=datetime.utcnow(),
    )
    assert SECRET not in out.target
    assert out.target == "postgresql://app:***@postgres:5432/hc"
    assert SECRET not in out.model_dump_json()


def test_api_output_keeps_env_and_http_targets_as_is():
    from agents.hyperhealth.models import CheckDefinitionOut

    for target in ("env:DATABASE_URL", "http://hypercode-core:8000/health"):
        out = CheckDefinitionOut(
            id=uuid.uuid4(), name="n", type="db", target=target, environment="production",
            interval_seconds=30, enabled=True, tags=[], created_at=datetime.utcnow(),
        )
        assert out.target == target
