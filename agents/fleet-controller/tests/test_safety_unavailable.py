import asyncio

import httpx
import pytest

import safety_client
from models import PlanRequest, RequestedAction


@pytest.fixture(autouse=True)
def _reset_client(monkeypatch):
    monkeypatch.setattr(safety_client, "_client", None)
    yield


def _plan():
    return PlanRequest(
        schema_version=1,
        mission_id="m1",
        requested_actions=[
            RequestedAction(action_id="a1", kind="compose_profile.preview", profile="agents")
        ],
    )


def _fake_client(status_code=200, payload=None, exc=None):
    class _Resp:
        def __init__(self):
            self.status_code = status_code

        def json(self):
            if isinstance(payload, Exception):
                raise payload
            return payload if payload is not None else {}

    class _Client:
        async def post(self, url, json=None, headers=None):
            if exc:
                raise exc
            return _Resp()

    return _Client()


def _check(client):
    async def _run():
        safety_client._client = client
        return await safety_client.check_infrastructure_mutation(_plan(), "sha256:deadbeef")

    return asyncio.run(_run())


def test_timeout_blocks():
    result = _check(_fake_client(exc=httpx.TimeoutException("timed out")))
    assert result.decision == "BLOCK"
    assert result.shepherd_available is False
    assert result.fail_closed is True


def test_connection_error_blocks():
    result = _check(_fake_client(exc=httpx.ConnectError("shepherd down")))
    assert result.decision == "BLOCK"
    assert result.shepherd_available is False


def test_non_200_blocks():
    result = _check(_fake_client(status_code=500))
    assert result.decision == "BLOCK"
    assert result.shepherd_available is False


def test_malformed_json_blocks():
    result = _check(_fake_client(payload=ValueError("not json")))
    assert result.decision == "BLOCK"
    assert result.shepherd_available is False


def test_missing_decision_field_blocks():
    result = _check(_fake_client(payload={"reason": "x"}))
    assert result.decision == "BLOCK"
    assert result.shepherd_available is False


def test_shepherd_allow_passes_through_not_fail_closed():
    result = _check(_fake_client(payload={"decision": "allow", "reason": "ok", "rule": "r1"}))
    assert result.decision == "ALLOW"
    assert result.shepherd_available is True
    assert result.fail_closed is False


def test_shepherd_escalate_passes_through():
    result = _check(_fake_client(payload={"decision": "escalate", "reason": "review needed"}))
    assert result.decision == "ESCALATE"
    assert result.shepherd_available is True
