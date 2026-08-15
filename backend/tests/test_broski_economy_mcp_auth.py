from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from starlette.testclient import TestClient


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def broski_economy_mcp_app(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("BROSKI_ECONOMY_MCP_AUTH_TOKEN", "test-secret-token")
    mod = _load_module(
        "hc_broski_economy_mcp_mod",
        Path(__file__).resolve().parents[2] / "agents" / "broski-economy-mcp" / "server.py",
    )
    return mod.app


def test_health_requires_no_auth(broski_economy_mcp_app):
    client = TestClient(broski_economy_mcp_app)
    resp = client.get("/health")
    assert resp.status_code == 200


def test_well_known_mcp_requires_auth(broski_economy_mcp_app):
    client = TestClient(broski_economy_mcp_app)
    resp = client.get("/.well-known/mcp")
    assert resp.status_code == 401


def test_tool_call_missing_auth_header_returns_401(broski_economy_mcp_app):
    client = TestClient(broski_economy_mcp_app)
    resp = client.post("/mcp/tools/nonexistent_tool", json={})
    assert resp.status_code == 401


def test_tool_call_wrong_token_returns_403(broski_economy_mcp_app):
    client = TestClient(broski_economy_mcp_app)
    resp = client.post(
        "/mcp/tools/nonexistent_tool",
        json={},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert resp.status_code == 403


def test_tool_call_valid_token_reaches_dispatcher(broski_economy_mcp_app):
    client = TestClient(broski_economy_mcp_app)
    resp = client.post(
        "/mcp/tools/nonexistent_tool",
        json={},
        headers={"Authorization": "Bearer test-secret-token"},
    )
    # NOT 404. This file's unknown-tool branch (line ~239-240) does
    # `return {"error": ...}, 404` — a plain tuple, which FastAPI does not
    # special-case into an HTTP 404; it serializes as a 200 with a
    # malformed JSON-array body `[{"error":...}, 404]`. Confirmed
    # empirically before this task started. That's a pre-existing bug in
    # the dispatcher, unrelated to auth and out of scope for this task —
    # do not fix it here. This test only needs to prove the valid token
    # reached the dispatcher at all (i.e. wasn't blocked by auth), so it
    # asserts the actual current behavior, not the status code a correct
    # implementation would return.
    assert resp.status_code == 200
    assert "Unknown tool" in resp.text


def test_non_ascii_token_returns_403_not_500(broski_economy_mcp_app):
    client = TestClient(broski_economy_mcp_app)
    # Starlette decodes incoming header bytes as latin-1, so a header byte
    # >= 0x80 on the wire becomes a non-ASCII str server-side. httpx's
    # TestClient rejects non-ASCII *str* header values before they ever
    # leave the client, so we pass the raw wire bytes directly (0xE9 =
    # latin-1 "é") to reproduce what actually reaches the server.
    resp = client.post(
        "/mcp/tools/nonexistent_tool",
        json={},
        headers={"Authorization": b"Bearer \xe9\xe9\xe9-not-a-real-token"},
    )
    # Non-ASCII bearer tokens must be rejected as invalid credentials
    # (403), not crash hmac.compare_digest into an unhandled 500.
    assert resp.status_code == 403


def test_secret_with_trailing_whitespace_still_matches(broski_economy_mcp_app, monkeypatch):
    monkeypatch.setenv("BROSKI_ECONOMY_MCP_AUTH_TOKEN", "test-secret-token\n")
    client = TestClient(broski_economy_mcp_app)
    resp = client.post(
        "/mcp/tools/nonexistent_tool",
        json={},
        headers={"Authorization": "Bearer test-secret-token"},
    )
    # A trailing newline in the provisioned secret must not break the
    # otherwise-correct token. Same pre-existing tuple-return quirk as
    # test_tool_call_valid_token_reaches_dispatcher above: the dispatcher
    # serializes as 200 with "Unknown tool" body, not a true 404.
    assert resp.status_code == 200
    assert "Unknown tool" in resp.text
