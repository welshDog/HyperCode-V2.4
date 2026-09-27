"""Governor's own copy of the plan schema — the container.restart literal (Phase 2b)."""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from models import RequestedAction  # noqa: E402


def test_container_restart_is_a_valid_kind():
    action = RequestedAction(action_id="restart-x", kind="container.restart", profile="skillweaver")
    assert action.kind == "container.restart" and action.profile == "skillweaver"


def test_existing_kinds_still_valid():
    RequestedAction(action_id="a", kind="compose_profile.preview")
    RequestedAction(action_id="b", kind="crew.workflow.preview")


def test_unknown_kind_still_rejected():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        RequestedAction(action_id="c", kind="compose_profile.start")


def test_fleet_controller_copy_is_unaffected():
    """The file-copy convention means fleet-controller's own copy must NOT gain this literal."""
    fc_models = pathlib.Path(__file__).resolve().parents[2] / "fleet-controller" / "models.py"
    text = fc_models.read_text(encoding="utf-8")
    assert "container.restart" not in text
    assert 'Literal["compose_profile.preview", "crew.workflow.preview"]' in text
