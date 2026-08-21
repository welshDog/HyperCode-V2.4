from sqlalchemy.orm import Session

from app.models.mission_evaluation import MissionEvaluation


def test_create_and_query_mission_evaluation(db: Session):
    row = MissionEvaluation(
        mission_id="mission_eval_test001",
        verdict="anomaly",
        checks={
            "status": "approved",
            "plan_malformed": False,
            "preview_failed": False,
            "safety_decision": "BLOCK",
            "shepherd_available": True,
            "human_decision": "approved",
            "anomaly_approved_despite_block": True,
            "anomaly_approved_despite_shepherd_down": False,
            "anomaly_rejected_despite_allow": False,
        },
        summary="approved despite BLOCK verdict",
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    assert row.mission_id == "mission_eval_test001"
    assert row.verdict == "anomaly"
    assert row.checks["anomaly_approved_despite_block"] is True
    assert row.evaluated_at is not None


def test_verdict_index_query(db: Session):
    db.add(
        MissionEvaluation(
            mission_id="mission_eval_test002",
            verdict="clean",
            checks={"status": "rejected_malformed"},
            summary="clean: rejected_malformed",
        )
    )
    db.commit()

    rows = db.query(MissionEvaluation).filter(MissionEvaluation.verdict == "clean").all()
    assert len(rows) == 1
    assert rows[0].mission_id == "mission_eval_test002"
