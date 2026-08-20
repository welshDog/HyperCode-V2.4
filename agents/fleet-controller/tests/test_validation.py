import pytest

from models import Constraints, PlanRequest, RequestedAction
from plan_validator import PlanValidationError, validate_plan


def _plan(**overrides):
    defaults = dict(
        schema_version=1,
        mission_id="mission_demo_001",
        requested_actions=[
            RequestedAction(action_id="a1", kind="compose_profile.preview", profile="agents")
        ],
        constraints=Constraints(allow_profiles=["agents"]),
    )
    defaults.update(overrides)
    return PlanRequest(**defaults)


def test_valid_plan_passes():
    validate_plan(_plan())  # must not raise


def test_empty_requested_actions_rejected():
    with pytest.raises(PlanValidationError, match="empty"):
        validate_plan(_plan(requested_actions=[]))


def test_duplicate_action_id_rejected():
    plan = _plan(
        requested_actions=[
            RequestedAction(action_id="dup", kind="compose_profile.preview", profile="agents"),
            RequestedAction(action_id="dup", kind="crew.workflow.preview"),
        ],
        constraints=Constraints(allow_profiles=["agents"]),
    )
    with pytest.raises(PlanValidationError, match="duplicate"):
        validate_plan(plan)


def test_prod_profile_hard_denied_even_if_allowed():
    plan = _plan(
        requested_actions=[
            RequestedAction(action_id="a1", kind="compose_profile.preview", profile="prod")
        ],
        # deliberately allow-listing "prod" — hard-deny must win anyway
        constraints=Constraints(allow_profiles=["prod"]),
    )
    with pytest.raises(PlanValidationError, match="hard-denied"):
        validate_plan(plan)


def test_gpu_profile_hard_denied():
    plan = _plan(
        requested_actions=[
            RequestedAction(action_id="a1", kind="compose_profile.preview", profile="gpu")
        ],
        constraints=Constraints(allow_profiles=["gpu"]),
    )
    with pytest.raises(PlanValidationError, match="hard-denied"):
        validate_plan(plan)


def test_profile_not_in_allow_list_rejected():
    plan = _plan(
        requested_actions=[
            RequestedAction(action_id="a1", kind="compose_profile.preview", profile="hyper")
        ],
        constraints=Constraints(allow_profiles=["agents"]),
    )
    with pytest.raises(PlanValidationError, match="not in allow_profiles"):
        validate_plan(plan)


def test_profile_in_deny_list_rejected():
    plan = _plan(
        requested_actions=[
            RequestedAction(action_id="a1", kind="compose_profile.preview", profile="agents")
        ],
        constraints=Constraints(allow_profiles=["agents"], deny_profiles=["agents"]),
    )
    with pytest.raises(PlanValidationError, match="denied by constraints"):
        validate_plan(plan)


def test_action_with_no_profile_skips_profile_checks():
    plan = _plan(
        requested_actions=[RequestedAction(action_id="a1", kind="crew.workflow.preview")],
        constraints=Constraints(),
    )
    validate_plan(plan)  # must not raise — no profile means nothing to check


# ── wire-level cases: pydantic rejects these before validate_plan ever runs ──


@pytest.mark.asyncio
async def test_unknown_action_kind_rejected_at_wire_level(client):
    body = {
        "schema_version": 1,
        "mission_id": "m1",
        "requested_actions": [{"action_id": "a1", "kind": "compose_profile.start"}],
        "constraints": {"allow_profiles": ["agents"]},
    }
    resp = await client.post("/v1/plans/preview", json=body)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_wrong_schema_version_rejected_at_wire_level(client):
    body = {
        "schema_version": 2,
        "mission_id": "m1",
        "requested_actions": [
            {"action_id": "a1", "kind": "compose_profile.preview", "profile": "agents"}
        ],
        "constraints": {"allow_profiles": ["agents"]},
    }
    resp = await client.post("/v1/plans/preview", json=body)
    assert resp.status_code == 422
