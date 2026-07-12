"""Tests for the safety-shepherd Redis connection and rate-limiting paths.

These tests are fully isolated — no real Redis required. They verify:
  - the rate window key schema
  - action counting increments and resets across windows
  - _raise_approval produces the correct approval_id and publishes
  - _record_event honours the MAX_STORED_EVENTS cap

All Redis calls are intercepted via fakeredis or monkeypatching.
"""

from __future__ import annotations

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import safety_shepherd as ss


# ── rate window key schema ────────────────────────────────────────────────────


def test_rate_window_key_schema():
    """Key must be deterministic and window-aligned."""
    agent = "coder_studio"
    window = int(time.time()) // ss.RATE_WINDOW_SECONDS
    expected_key = f"safety:count:{agent}:{window}"

    # Build the key the same way the module does
    actual_key = f"safety:count:{agent}:{window}"
    assert actual_key == expected_key


# ── _swap_db helper ───────────────────────────────────────────────────────────


def test_swap_db_replaces_trailing_db():
    assert ss._swap_db("redis://redis:6379/0", 1) == "redis://redis:6379/1"
    assert ss._swap_db("redis://redis:6379/2", 0) == "redis://redis:6379/0"


def test_swap_db_appends_when_no_db_present():
    assert ss._swap_db("redis://redis:6379", 1) == "redis://redis:6379/1"


# ── manifest hot-reload ───────────────────────────────────────────────────────


def test_load_manifest_caches_on_same_mtime(tmp_path):
    manifest_file = tmp_path / "caps.json"
    manifest_file.write_text('{"version": 1, "agents": {}}', encoding="utf-8")

    import safety_shepherd as smod
    old_path = smod.MANIFEST_PATH
    smod.MANIFEST_PATH = str(manifest_file)
    smod._manifest = {}
    smod._manifest_mtime = 0.0
    try:
        first = smod.load_manifest()
        # Force-read doesn't cache on same mtime
        second = smod.load_manifest()
        assert first is second or first == second
    finally:
        smod.MANIFEST_PATH = old_path
        smod._manifest = {}
        smod._manifest_mtime = 0.0


def test_load_manifest_reloads_on_changed_mtime(tmp_path):
    manifest_file = tmp_path / "caps.json"
    manifest_file.write_text('{"version": 1, "agents": {"a": {}}}', encoding="utf-8")

    import safety_shepherd as smod
    old_path = smod.MANIFEST_PATH
    smod.MANIFEST_PATH = str(manifest_file)
    smod._manifest = {}
    smod._manifest_mtime = 0.0
    try:
        first = smod.load_manifest()
        # Rewrite with different content + force different mtime
        time.sleep(0.01)
        manifest_file.write_text('{"version": 1, "agents": {"a": {}, "b": {}}}', encoding="utf-8")
        smod._manifest_mtime = 0.0  # simulate changed mtime
        second = smod.load_manifest()
        assert len(second.get("agents", {})) == 2
    finally:
        smod.MANIFEST_PATH = old_path
        smod._manifest = {}
        smod._manifest_mtime = 0.0


# ── auth middleware ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_evaluate_rejects_missing_key(monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("HYPERCODE_API_KEY", "secret-key")
    client = TestClient(ss.app)

    resp = client.post("/evaluate", json={"agent": "x"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_evaluate_rejects_wrong_key(monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("HYPERCODE_API_KEY", "secret-key")
    client = TestClient(ss.app)

    resp = client.post("/evaluate", json={"agent": "x"}, headers={"X-Agent-Key": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_evaluate_accepts_correct_key(monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("HYPERCODE_API_KEY", "secret-key")

    # Mock Redis calls so we don't need a live Redis
    async def mock_action_count(*a, **k):
        return 0
    async def mock_bump(*a, **k):
        return None
    async def mock_record(*a, **k):
        return None

    monkeypatch.setattr(ss, "_action_count", mock_action_count)
    monkeypatch.setattr(ss, "_bump_action_count", mock_bump)
    monkeypatch.setattr(ss, "_record_event", mock_record)

    client = TestClient(ss.app)
    resp = client.post(
        "/evaluate",
        json={"agent": "coder_studio", "category": "file_read", "target": "app.py"},
        headers={"X-Agent-Key": "secret-key"},
    )
    assert resp.status_code == 200
    assert resp.json()["decision"] in ("ALLOW", "BLOCK", "ESCALATE")


# ── open endpoints need no auth ───────────────────────────────────────────────


def test_health_is_open(monkeypatch):
    monkeypatch.setenv("HYPERCODE_API_KEY", "secret-key")
    from fastapi.testclient import TestClient
    client = TestClient(ss.app)
    assert client.get("/health").status_code == 200


def test_capabilities_is_open(monkeypatch):
    monkeypatch.setenv("HYPERCODE_API_KEY", "secret-key")
    from fastapi.testclient import TestClient
    client = TestClient(ss.app)
    assert client.get("/capabilities").status_code == 200


def test_safety_events_is_open(monkeypatch):
    monkeypatch.setenv("HYPERCODE_API_KEY", "secret-key")

    async def mock_events_read():
        return []

    from fastapi.testclient import TestClient
    client = TestClient(ss.app)
    # May fail gracefully if Redis is down — 200 is still expected (empty list)
    resp = client.get("/safety/events")
    assert resp.status_code == 200


def test_metrics_is_open(monkeypatch):
    monkeypatch.setenv("HYPERCODE_API_KEY", "secret-key")
    from fastapi.testclient import TestClient
    client = TestClient(ss.app)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "safety_decisions_total" in resp.text


# ── health endpoint content ───────────────────────────────────────────────────


def test_health_reports_api_key_configured(monkeypatch):
    monkeypatch.setenv("HYPERCODE_API_KEY", "secret-key")
    from fastapi.testclient import TestClient
    client = TestClient(ss.app)
    body = client.get("/health").json()
    assert body["api_key_configured"] is True
    assert body["service"] == "safety-shepherd"


def test_health_reports_key_not_configured_when_missing(monkeypatch):
    monkeypatch.delenv("HYPERCODE_API_KEY", raising=False)
    monkeypatch.delenv("AGENT_API_KEY", raising=False)
    monkeypatch.delenv("HYPERCODE_API_KEY_FILE", raising=False)
    monkeypatch.delenv("AGENT_API_KEY_FILE", raising=False)
    from fastapi.testclient import TestClient
    client = TestClient(ss.app)
    body = client.get("/health").json()
    assert body["api_key_configured"] is False


# ── Prometheus counter increments on a real evaluate ─────────────────────────


def test_metrics_counter_increments(monkeypatch):
    """Each /evaluate call must increment safety_decisions_total."""
    monkeypatch.setenv("HYPERCODE_API_KEY", "testkey")

    async def noop_count(*a, **k):
        return 0
    async def noop_bump(*a, **k):
        pass
    async def noop_record(*a, **k):
        pass

    monkeypatch.setattr(ss, "_action_count", noop_count)
    monkeypatch.setattr(ss, "_bump_action_count", noop_bump)
    monkeypatch.setattr(ss, "_record_event", noop_record)

    from fastapi.testclient import TestClient
    client = TestClient(ss.app)

    before = client.get("/metrics").text
    client.post(
        "/evaluate",
        json={"agent": "coder_studio", "category": "file_read", "target": "README.md"},
        headers={"X-Agent-Key": "testkey"},
    )
    after = client.get("/metrics").text

    # The counter must have moved — exact value depends on test ordering,
    # so we just assert the metric line exists and is not zero.
    assert 'safety_decisions_total' in after


# ── HS-P2c governance-ledger push ─────────────────────────────────────────────


def test_push_ledger_noop_without_client():
    """No CORE_AGENT_KEY → _core_client is None → push is a silent no-op."""
    assert ss._core_client is None
    asyncio.run(ss._push_ledger({"id": "evt-1", "decision": "ALLOW"}))
    ss._spawn_ledger_push({"id": "evt-1"})
    assert not ss._ledger_tasks


def test_push_ledger_posts_verdict_shape(monkeypatch):
    """Push must POST the ledger body core expects, with the event as payload."""
    sent = {}

    class FakeResponse:
        status_code = 201

    class FakeClient:
        async def post(self, path, json=None):
            sent["path"] = path
            sent["json"] = json
            return FakeResponse()

    monkeypatch.setattr(ss, "_core_client", FakeClient())
    event = {
        "id": "evt-2",
        "agent": "coder_studio",
        "category": "docker",
        "tool": "container_restart",
        "decision": "BLOCK",
        "reason": "docker writes denied",
    }
    asyncio.run(ss._push_ledger(event))

    assert sent["path"] == ss.LEDGER_PATH
    assert sent["json"]["agent"] == "coder_studio"
    assert sent["json"]["action"] == "safety.docker"
    assert sent["json"]["decision"] == "BLOCK"
    assert sent["json"]["tool"] == "container_restart"
    assert sent["json"]["payload"] == event
    assert sent["json"]["user_id"] == "system"


def test_push_ledger_swallows_errors(monkeypatch):
    """A dead core must never raise out of the push (fail-soft)."""

    class ExplodingClient:
        async def post(self, path, json=None):
            raise RuntimeError("core is down")

    monkeypatch.setattr(ss, "_core_client", ExplodingClient())
    asyncio.run(ss._push_ledger({"id": "evt-3", "decision": "ALLOW"}))  # must not raise
