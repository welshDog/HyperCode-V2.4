from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


module_dir = str(Path(__file__).resolve().parents[1])
if module_dir not in sys.path:
    sys.path.insert(0, module_dir)

import main as orchestrator_main  # noqa: E402


def _sha256(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def test_execute_smoke_noop_requires_headers_and_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    key = "bench-key-123"
    monkeypatch.setenv("SMOKE_ENDPOINT_ENABLED", "true")
    monkeypatch.setenv("SMOKE_KEY_ALLOWLIST", _sha256(key))
    monkeypatch.setenv("SMOKE_KEY_TTL_SECONDS", "900")

    orchestrator_main._smoke_key_issued_at.clear()
    orchestrator_main._smoke_key_revoked_at.clear()

    client = TestClient(orchestrator_main.app)
    r = client.post("/execute/smoke", json={"mode": "noop"})
    assert r.status_code in {401, 403, 404, 422, 503}

    r = client.post(
        "/execute/smoke",
        headers={"X-Smoke-Mode": "true", "X-API-Key": key},
        json={"mode": "noop"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["smoke"] == "pass"
    assert data["mode"] == "noop"
    assert data["approval_skipped"] is True


def test_execute_smoke_ttl_revokes_key(monkeypatch: pytest.MonkeyPatch) -> None:
    key = "bench-key-ttl"
    monkeypatch.setenv("SMOKE_ENDPOINT_ENABLED", "true")
    monkeypatch.setenv("SMOKE_KEY_ALLOWLIST", _sha256(key))
    monkeypatch.setenv("SMOKE_KEY_TTL_SECONDS", "0")

    orchestrator_main._smoke_key_issued_at.clear()
    orchestrator_main._smoke_key_revoked_at.clear()

    client = TestClient(orchestrator_main.app)
    r1 = client.post(
        "/execute/smoke",
        headers={"X-Smoke-Mode": "true", "X-API-Key": key},
        json={"mode": "noop"},
    )
    assert r1.status_code == 200

    r2 = client.post(
        "/execute/smoke",
        headers={"X-Smoke-Mode": "true", "X-API-Key": key},
        json={"mode": "noop"},
    )
    assert r2.status_code == 403
