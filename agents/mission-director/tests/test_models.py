# agents/mission-director/tests/test_models.py
import pytest
from pydantic import ValidationError

from models import MissionProposal, PlanRequest, ReviewDecision


def test_mission_proposal_minimal_valid():
    proposal = MissionProposal(
        schema_version=1,
        mission_id="mission_abc123",
        goal="do the thing",
        status="proposed",
    )
    assert proposal.status == "proposed"
    assert proposal.plan is None


def test_mission_proposal_rejects_unknown_status():
    with pytest.raises(ValidationError):
        MissionProposal(
            schema_version=1,
            mission_id="mission_abc123",
            goal="do the thing",
            status="not_a_real_status",
        )


def test_mission_proposal_full_shape():
    plan = PlanRequest(schema_version=1, mission_id="mission_abc123", requested_actions=[])
    proposal = MissionProposal(
        schema_version=1,
        mission_id="mission_abc123",
        goal="do the thing",
        truth_snapshot_ref="sha256:abc",
        rationale="because",
        plan=plan,
        status="previewed",
    )
    assert proposal.plan.mission_id == "mission_abc123"


def test_review_decision_accepts_approve_and_reject():
    assert ReviewDecision(decision="approve").decision == "approve"
    assert ReviewDecision(decision="reject").decision == "reject"


def test_review_decision_rejects_other_values():
    with pytest.raises(ValidationError):
        ReviewDecision(decision="maybe")


from models import ImpactView


def test_mission_proposal_impact_defaults_to_empty_list():
    proposal = MissionProposal(
        schema_version=1,
        mission_id="mission_abc123",
        goal="do the thing",
        status="proposed",
    )
    assert proposal.impact == []


def test_impact_view_degraded_shape():
    view = ImpactView(profile="agents", available=False, reason="registry unavailable")
    assert view.upstream == []
    assert view.downstream_already_running == []
    assert view.reason == "registry unavailable"
