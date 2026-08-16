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
def rest_adapter_app(monkeypatch):
    monkeypatch.setenv("MCP_REST_ADAPTER_AUTH_TOKEN", "test-secret-token")
    mod = _load_module(
        "hc_mcp_rest_adapter_mod",
        Path(__file__).resolve().parents[2] / "services" / "mcp-rest-adapter" / "app.py",
    )
    return mod.app


def test_health_requires_no_auth(rest_adapter_app):
    client = TestClient(rest_adapter_app)
    resp = client.get("/health")
    assert resp.status_code == 200


def test_tools_discover_missing_auth_header_returns_401(rest_adapter_app):
    client = TestClient(rest_adapter_app)
    resp = client.get("/tools/discover")
    assert resp.status_code == 401


def test_tools_discover_wrong_token_returns_403(rest_adapter_app):
    client = TestClient(rest_adapter_app)
    resp = client.get("/tools/discover", headers={"Authorization": "Bearer wrong-token"})
    assert resp.status_code == 403


def test_tool_call_missing_auth_header_returns_401(rest_adapter_app):
    client = TestClient(rest_adapter_app)
    resp = client.post("/tools/call", json={"tool": "not_a_real_tool"})
    assert resp.status_code == 401


def test_tool_call_wrong_token_returns_403(rest_adapter_app):
    client = TestClient(rest_adapter_app)
    resp = client.post(
        "/tools/call",
        json={"tool": "not_a_real_tool"},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert resp.status_code == 403


def test_tool_call_valid_token_reaches_handler(rest_adapter_app):
    client = TestClient(rest_adapter_app)
    resp = client.post(
        "/tools/call",
        json={"tool": "not_a_real_tool"},
        headers={"Authorization": "Bearer test-secret-token"},
    )
    # 400 ("Unsupported tool/action format") proves auth passed — the
    # request reached _normalize_tool_call, which runs entirely locally
    # with no network call to the upstream gateway.
    assert resp.status_code == 400


def test_non_ascii_token_returns_403_not_500(rest_adapter_app):
    client = TestClient(rest_adapter_app)
    # Starlette decodes incoming header bytes as latin-1, so a header byte
    # >= 0x80 on the wire becomes a non-ASCII str server-side. httpx's
    # TestClient rejects non-ASCII *str* header values before they ever
    # leave the client, so we pass the raw wire bytes directly (0xE9 =
    # latin-1 "é") to reproduce what actually reaches the server.
    resp = client.post(
        "/tools/call",
        json={"tool": "not_a_real_tool"},
        headers={"Authorization": b"Bearer \xe9\xe9\xe9-not-a-real-token"},
    )
    # Non-ASCII bearer tokens must be rejected as invalid credentials
    # (403), not crash hmac.compare_digest into an unhandled 500.
    assert resp.status_code == 403


def test_secret_with_trailing_whitespace_still_matches(rest_adapter_app, monkeypatch):
    monkeypatch.setenv("MCP_REST_ADAPTER_AUTH_TOKEN", "test-secret-token\n")
    client = TestClient(rest_adapter_app)
    resp = client.post(
        "/tools/call",
        json={"tool": "not_a_real_tool"},
        headers={"Authorization": "Bearer test-secret-token"},
    )
    # A trailing newline in the provisioned secret must not break the
    # otherwise-correct token — same outcome as the clean-secret case
    # above: 400 (auth passed, dispatcher's format check reached).
    assert resp.status_code == 400
