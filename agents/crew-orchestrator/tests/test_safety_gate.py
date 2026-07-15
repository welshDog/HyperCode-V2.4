"""Tests for the Safety Shepherd dispatch gate (P0-2 remaining intercept)."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

import safety_gate


@pytest.fixture(autouse=True)
def _reset_gate(monkeypatch):
    """Each test gets a clean module state and monitor-mode defaults."""
    monkeypatch.setattr(safety_gate, "_client", None)
    monkeypatch.delenv("SAFETY_SHEPHERD_MODE", raising=False)
    yield


def _fake_client(status_code=200, payload=None, exc=None):
    client = MagicMock()

    async def post(url, json=None, headers=None):
        if exc:
            raise exc
        resp = MagicMock()
        resp.status_code = status_code
        resp.json.return_value = payload if payload is not None else {}
        return resp

    client.post = post
    return client


# ── evaluate_dispatch ─────────────────────────────────────────────────────────


def test_off_mode_skips_the_call(monkeypatch):
    monkeypatch.setenv("SAFETY_SHEPHERD_MODE", "off")
    verdict = asyncio.run(safety_gate.evaluate_dispatch("coder", "code_generation", "t1"))
    assert verdict == {"decision": "ALLOW", "mode": "off", "skipped": True}


def test_verdict_passes_through(monkeypatch):
    monkeypatch.setenv("SAFETY_SHEPHERD_MODE", "enforce")
    monkeypatch.setattr(
        safety_gate,
        "_client",
        _fake_client(payload={"decision": "block", "reason": "denied", "rule": "r1"}),
    )
    verdict = asyncio.run(safety_gate.evaluate_dispatch("coder", None, "t2", "risky task"))
    assert verdict["decision"] == "BLOCK"  # normalised to upper
    assert verdict["mode"] == "enforce"
    assert verdict["skipped"] is False
    assert verdict["reason"] == "denied"


def test_http_error_fails_open(monkeypatch):
    monkeypatch.setattr(safety_gate, "_client", _fake_client(status_code=500))
    verdict = asyncio.run(safety_gate.evaluate_dispatch("coder", None, "t3"))
    assert verdict["decision"] == safety_gate.ALLOW
    assert verdict["skipped"] is True


def test_unreachable_shepherd_fails_open(monkeypatch):
    monkeypatch.setattr(
        safety_gate, "_client", _fake_client(exc=ConnectionError("shepherd down"))
    )
    verdict = asyncio.run(safety_gate.evaluate_dispatch("coder", None, "t4"))
    assert verdict["decision"] == safety_gate.ALLOW
    assert verdict["skipped"] is True


def test_malformed_body_fails_open(monkeypatch):
    monkeypatch.setattr(safety_gate, "_client", _fake_client(payload=["not", "a", "dict"]))
    verdict = asyncio.run(safety_gate.evaluate_dispatch("coder", None, "t5"))
    assert verdict["skipped"] is True


# ── is_enforced ───────────────────────────────────────────────────────────────


def test_is_enforced_only_for_real_enforce_verdicts():
    assert safety_gate.is_enforced({"mode": "enforce", "skipped": False}) is True
    assert safety_gate.is_enforced({"mode": "enforce", "skipped": True}) is False
    assert safety_gate.is_enforced({"mode": "monitor", "skipped": False}) is False


# ── wait_for_shepherd_approval ────────────────────────────────────────────────


def test_approval_wait_denies_without_id():
    assert asyncio.run(safety_gate.wait_for_shepherd_approval(AsyncMock(), None)) is False


def test_approval_wait_reads_response_key():
    r = AsyncMock()
    r.get.return_value = json.dumps({"status": "approved"})
    assert asyncio.run(safety_gate.wait_for_shepherd_approval(r, "ap-1")) is True
    r.get.assert_awaited_with("approval:ap-1:response")


def test_approval_wait_denied_status():
    r = AsyncMock()
    r.get.return_value = json.dumps({"status": "denied"})
    assert asyncio.run(safety_gate.wait_for_shepherd_approval(r, "ap-2")) is False


def test_approval_wait_times_out(monkeypatch):
    monkeypatch.setenv("SAFETY_APPROVAL_TIMEOUT", "0")
    r = AsyncMock()
    r.get.return_value = None
    assert asyncio.run(safety_gate.wait_for_shepherd_approval(r, "ap-3")) is False
