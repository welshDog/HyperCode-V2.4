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
def stripe_mcp_app(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_dummy")
    monkeypatch.setenv("STRIPE_MCP_AUTH_TOKEN", "test-secret-token")
    mod = _load_module(
        "hc_stripe_mcp_mod",
        Path(__file__).resolve().parents[2] / "agents" / "stripe-mcp" / "server.py",
    )
    return mod.app


def test_health_requires_no_auth(stripe_mcp_app):
    client = TestClient(stripe_mcp_app)
    resp = client.get("/health")
    assert resp.status_code == 200


def test_well_known_mcp_requires_auth(stripe_mcp_app):
    client = TestClient(stripe_mcp_app)
    resp = client.get("/.well-known/mcp")
    assert resp.status_code == 401


def test_resource_plans_requires_auth(stripe_mcp_app):
    client = TestClient(stripe_mcp_app)
    resp = client.get("/mcp/resources/stripe://plans")
    assert resp.status_code == 401


def test_tool_call_missing_auth_header_returns_401(stripe_mcp_app):
    client = TestClient(stripe_mcp_app)
    resp = client.post("/mcp/tools/nonexistent_tool", json={})
    assert resp.status_code == 401


def test_tool_call_wrong_token_returns_403(stripe_mcp_app):
    client = TestClient(stripe_mcp_app)
    resp = client.post(
        "/mcp/tools/nonexistent_tool",
        json={},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert resp.status_code == 403


def test_tool_call_valid_token_reaches_dispatcher(stripe_mcp_app):
    client = TestClient(stripe_mcp_app)
    resp = client.post(
        "/mcp/tools/nonexistent_tool",
        json={},
        headers={"Authorization": "Bearer test-secret-token"},
    )
    # 404 (unknown tool) proves auth passed — the request reached the
    # dispatcher's own unknown-tool check, unchanged by this fix.
    assert resp.status_code == 404
