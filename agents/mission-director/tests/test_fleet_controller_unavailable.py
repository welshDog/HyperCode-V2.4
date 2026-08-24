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


@pytest.mark.asyncio
async def test_create_plan_route_returns_rejected_malformed_on_empty_actions(client, monkeypatch):
    import main

    async def _fake_generate_empty_actions(goal):
        return LLMPlanOutput(rationale="r", requested_actions=[])

    monkeypatch.setattr(main, "get_snapshot_ref", lambda: "sha256:test")
    monkeypatch.setattr(main.plan_generator, "generate", _fake_generate_empty_actions)

    resp = await client.post("/v1/plan", json={"mission_id": "mission_t4", "goal": "x"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "rejected_malformed"
    assert body["plan"] is not None  # plan was built before local_validator rejected it
    assert body["plan_response"] is None


@pytest.mark.asyncio
async def test_create_plan_route_returns_previewed_on_full_success(client, monkeypatch):
    import main
    from models import ExecutionView, PlanResponse, SafetyView

    async def _fake_generate(goal):
        return LLMPlanOutput(
            rationale="r",
            requested_actions=[RequestedAction(action_id="a1", kind="compose_profile.preview")],
        )

    async def _fake_preview(plan):
        return PlanResponse(
            plan_id="plan_test1",
            plan_hash="sha256:testhash",
            safety=SafetyView(decision="ESCALATE", reason="dangerous category", shepherd_available=True),
            execution=ExecutionView(performed=False, would_execute=[]),
        )

    monkeypatch.setattr(main, "get_snapshot_ref", lambda: "sha256:test")
    monkeypatch.setattr(main.plan_generator, "generate", _fake_generate)
    monkeypatch.setattr(main.fleet_client, "preview", _fake_preview)

    resp = await client.post("/v1/plan", json={"mission_id": "mission_t5", "goal": "x"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "previewed"
    assert body["plan_response"]["execution"]["performed"] is False
    assert body["plan_response"]["safety"]["decision"] == "ESCALATE"


@pytest.mark.asyncio
async def test_create_plan_route_includes_impact_for_profile_actions(client, monkeypatch):
    import main
    from models import ExecutionView, ImpactView, PlanResponse, SafetyView

    async def _fake_generate(goal):
        return LLMPlanOutput(
            rationale="r",
            requested_actions=[
                RequestedAction(action_id="a1", kind="compose_profile.preview", profile="agents")
            ],
        )

    async def _fake_preview(plan):
        return PlanResponse(
            plan_id="plan_test6",
            plan_hash="sha256:testhash6",
            safety=SafetyView(decision="ESCALATE", reason="dangerous category", shepherd_available=True),
            execution=ExecutionView(performed=False, would_execute=[]),
        )

    def _fake_get_impact(profiles):
        assert profiles == ["agents"]
        return [
            ImpactView(
                profile="agents",
                upstream=["postgres"],
                downstream_already_running=[],
                available=True,
            )
        ]

    monkeypatch.setattr(main, "get_snapshot_ref", lambda: "sha256:test")
    monkeypatch.setattr(main.plan_generator, "generate", _fake_generate)
    monkeypatch.setattr(main.fleet_client, "preview", _fake_preview)
    monkeypatch.setattr(main.impact_snapshot, "get_impact", _fake_get_impact)

    resp = await client.post("/v1/plan", json={"mission_id": "mission_t6", "goal": "x"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "previewed"
    assert body["impact"] == [
        {
            "profile": "agents",
            "upstream": ["postgres"],
            "downstream_already_running": [],
            "available": True,
            "reason": None,
        }
    ]
