# agents/mission-director/tests/test_local_validator.py
import pytest

from local_validator import LocalValidationError, validate
from models import PlanRequest, RequestedAction


def _plan(actions):
    return PlanRequest(schema_version=1, mission_id="mission_x", requested_actions=actions)


def test_validate_passes_with_actions_and_snapshot_ref():
    plan = _plan([RequestedAction(action_id="a1", kind="compose_profile.preview")])
    validate(plan, "sha256:abc")  # no raise


def test_validate_rejects_empty_actions():
    plan = _plan([])
    with pytest.raises(LocalValidationError, match="requested_actions"):
        validate(plan, "sha256:abc")


def test_validate_rejects_missing_snapshot_ref():
    plan = _plan([RequestedAction(action_id="a1", kind="compose_profile.preview")])
    with pytest.raises(LocalValidationError, match="truth_snapshot_ref"):
        validate(plan, None)


def test_validate_rejects_empty_snapshot_ref():
    plan = _plan([RequestedAction(action_id="a1", kind="compose_profile.preview")])
    with pytest.raises(LocalValidationError, match="truth_snapshot_ref"):
        validate(plan, "")
