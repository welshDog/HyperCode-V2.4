import json

import httpx
import pytest

import shepherd_client as sc


def _transport(handler):
    """Helper: transport."""
    return httpx.MockTransport(handler)


@pytest.fixture(autouse=True)
async def _reset():
    """Helper: reset."""
    yield
    await sc.aclose()


async def _run_with(monkeypatch, handler):
    """Helper: run with."""
    client = httpx.AsyncClient(transport=_transport(handler), timeout=3.0)
    monkeypatch.setattr(sc, "_get_client", lambda: client)
    return await sc.evaluate_plan(
        mission_id="m", plan_hash="sha256:x", action="compose_profile.preview", target="agents"
    )


@pytest.mark.asyncio
async def test_structured_verdict_parsed(monkeypatch):
    """Test structured verdict parsed."""
    captured = []

    def handler(request):
        """Helper: handler."""
        captured.append(json.loads(request.content))
        return httpx.Response(200, json={
            "decision": "ESCALATE", "reason": "runtime state",
            "risk_class": "INFRASTRUCTURE_MUTATION", "policy_version": "safety-2026-09-04.1",
            "allowed_actions": ["compose_profile.preview"], "blocked_actions": ["compose_profile.start"],
            "event_id": "evt_1",
        })
    v = await _run_with(monkeypatch, handler)
    assert v.decision == "ESCALATE"
    assert v.risk_class == "INFRASTRUCTURE_MUTATION"
    assert v.policy_version == "safety-2026-09-04.1"
    assert v.blocked_actions == ["compose_profile.start"]
    assert v.shepherd_available is True
    assert v.fail_closed is False

    body = captured[0]
    assert body["agent"] == "governor"
    assert body["category"] == "docker"
    assert body["tool"] == "compose_profile.preview"
    assert body["target"] == "agents"
    assert body["domain"] is None
    assert body["context"] == {"mission_id": "m", "plan_hash": "sha256:x"}


@pytest.mark.asyncio
@pytest.mark.parametrize("handler", [
    lambda request: httpx.Response(500, text="boom"),
    lambda request: httpx.Response(200, text="not json"),
    lambda request: httpx.Response(200, json={"reason": "no decision key"}),
])
async def test_fail_closed_paths(monkeypatch, handler):
    """Test fail closed paths."""
    v = await _run_with(monkeypatch, handler)
    assert v.decision == "BLOCK"
    assert v.shepherd_available is False
    assert v.fail_closed is True
    assert v is sc._FAIL_CLOSED


@pytest.mark.asyncio
async def test_connection_error_fail_closed(monkeypatch):
    """Test connection error fail closed."""
    def handler(request):
        """Helper: handler."""
        raise httpx.ConnectError("refused")
    v = await _run_with(monkeypatch, handler)
    assert v.fail_closed is True
    assert v.risk_class == "INFRASTRUCTURE_MUTATION"
    assert v is sc._FAIL_CLOSED
