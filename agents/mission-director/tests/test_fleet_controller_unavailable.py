# agents/mission-director/tests/test_fleet_controller_unavailable.py
import pytest

import fleet_client
import plan_generator
from plan_generator import LLMPlanOutput
from models import RequestedAction


@pytest.mark.asyncio
async def test_create_plan_route_returns_preview_unavailable_on_fleet_controller_down(
    client, monkeypatch
):
    import main

    async def _fake_generate(goal):
        return LLMPlanOutput(
            rationale="r",
            requested_actions=[RequestedAction(action_id="a1", kind="compose_profile.preview")],
        )

    async def _fake_preview(plan):
        raise fleet_client.FleetControllerUnavailable("connection refused")

    monkeypatch.setattr(main, "get_snapshot_ref", lambda: "sha256:test")
    monkeypatch.setattr(main.plan_generator, "generate", _fake_generate)
    monkeypatch.setattr(main.fleet_client, "preview", _fake_preview)

    resp = await client.post("/v1/plan", json={"mission_id": "mission_t2", "goal": "x"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "preview_unavailable"
    assert body["plan"] is not None  # plan was built before the failed call
    assert body["plan_response"] is None


@pytest.mark.asyncio
async def test_create_plan_route_returns_preview_unavailable_when_truth_registry_fails(
    client, monkeypatch
):
    import main

    def _raise_registry_error():
        raise RuntimeError("registry unavailable")

    monkeypatch.setattr(main, "get_snapshot_ref", _raise_registry_error)

    resp = await client.post("/v1/plan", json={"mission_id": "mission_t3", "goal": "x"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "preview_unavailable"
    assert body["plan"] is None  # never reached the LLM or fleet-controller
