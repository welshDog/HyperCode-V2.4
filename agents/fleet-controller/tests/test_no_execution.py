import sys

import pytest

import safety_client
from safety_client import SafetyResult


VALID_PLAN = {
    "schema_version": 1,
    "mission_id": "m1",
    "requested_actions": [
        {"action_id": "a1", "kind": "compose_profile.preview", "profile": "agents"}
    ],
    "constraints": {"allow_profiles": ["agents"]},
}


@pytest.fixture(autouse=True)
def _reset_client(monkeypatch):
    monkeypatch.setattr(safety_client, "_client", None)
    yield


async def _mock_shepherd(monkeypatch, result: SafetyResult):
    async def _fake(plan, plan_hash):
        return result

    monkeypatch.setattr(safety_client, "check_infrastructure_mutation", _fake)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "result",
    [
        SafetyResult(decision="ALLOW", reason="ok", shepherd_available=True),
        SafetyResult(decision="BLOCK", reason="denied", shepherd_available=True),
        SafetyResult(decision="ESCALATE", reason="needs review", shepherd_available=True),
        SafetyResult(
            decision="BLOCK",
            reason="Safety Shepherd unavailable; fail-closed",
            shepherd_available=False,
            fail_closed=True,
        ),
    ],
)
async def test_execution_never_performed_regardless_of_shepherd_verdict(
    client, monkeypatch, result
):
    await _mock_shepherd(monkeypatch, result)
    resp = await client.post("/v1/plans/preview", json=VALID_PLAN)
    assert resp.status_code == 200
    body = resp.json()
    assert body["execution"]["performed"] is False
    assert body["execution"]["would_execute"] == []


def test_no_docker_module_imported_anywhere():
    import main  # noqa: F401 — import is the assertion

    assert "docker" not in sys.modules


def test_main_has_no_dispatch_or_docker_attribute():
    import main

    suspicious = [
        name
        for name in dir(main)
        if "dispatch" in name.lower() or "docker" in name.lower() or "execute" in name.lower()
    ]
    assert suspicious == []
