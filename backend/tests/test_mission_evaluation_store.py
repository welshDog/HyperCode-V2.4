# backend/tests/test_mission_evaluation_store.py
from sqlalchemy.orm import Session

from app.models.mission import MissionProposal
from app.services import mission_evaluation_store


def _seed_proposal(db: Session, mission_id: str, status: str, plan_response=None):
    db.add(
        MissionProposal(
            mission_id=mission_id,
            status=status,
            goal="g",
            truth_snapshot_ref="sha256:abc",
            plan=None,
            plan_response=plan_response,
        )
    )
    db.commit()


def test_run_evaluation_evaluates_terminal_missions_only(db: Session):
    _seed_proposal(db, "mission_e1", "rejected_malformed")
    _seed_proposal(db, "mission_e2", "previewed")  # not terminal, must be skipped

    result = mission_evaluation_store.run_evaluation(db)
    assert result["evaluated_count"] == 1
    assert result["already_evaluated_skipped"] == 0


def test_run_evaluation_is_idempotent(db: Session):
    _seed_proposal(db, "mission_e3", "preview_unavailable")

    first = mission_evaluation_store.run_evaluation(db)
    assert first["evaluated_count"] == 1

    second = mission_evaluation_store.run_evaluation(db)
    assert second["evaluated_count"] == 0
    assert second["already_evaluated_skipped"] == 1


def test_run_evaluation_flags_the_flagship_anomaly(db: Session):
    _seed_proposal(
        db,
        "mission_e4",
        "approved",
        plan_response={"safety": {"decision": "BLOCK", "shepherd_available": True}},
    )

    result = mission_evaluation_store.run_evaluation(db)
    assert result["evaluated_count"] == 1
    assert result["anomaly_count"] == 1


def test_list_evaluations_filters_by_verdict(db: Session):
    _seed_proposal(db, "mission_e5", "rejected_malformed")
    _seed_proposal(
        db,
        "mission_e6",
        "approved",
        plan_response={"safety": {"decision": "BLOCK", "shepherd_available": True}},
    )
    mission_evaluation_store.run_evaluation(db)

    total, anomalies = mission_evaluation_store.list_evaluations(db, verdict="anomaly")
    assert total == 1
    assert anomalies[0].mission_id == "mission_e6"

    total_clean, clean_rows = mission_evaluation_store.list_evaluations(db, verdict="clean")
    assert total_clean == 1
    assert clean_rows[0].mission_id == "mission_e5"


def test_summary_with_zero_evaluations(db: Session):
    result = mission_evaluation_store.summary(db)
    assert result["total_evaluated"] == 0
    assert result["plan_malformed_rate"] == 0.0
    assert result["anomaly_approved_despite_block_count"] == 0


def test_summary_computes_rates_correctly(db: Session):
    _seed_proposal(db, "mission_e7", "rejected_malformed")
    _seed_proposal(db, "mission_e8", "approved", plan_response={"safety": {"decision": "ALLOW", "shepherd_available": True}})
    mission_evaluation_store.run_evaluation(db)

    result = mission_evaluation_store.summary(db)
    assert result["total_evaluated"] == 2
    assert result["plan_malformed_rate"] == 0.5
    assert result["human_approved_count"] == 1
