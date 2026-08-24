from sqlalchemy.orm import Session

from app.services import mission_store


def test_create_and_get_round_trip(db: Session):
    row = mission_store.create(
        db,
        mission_id="mission_test001",
        status="previewed",
        goal="test goal",
        truth_snapshot_ref="sha256:abc",
        plan={"schema_version": 1, "requested_actions": []},
        plan_response={"plan_id": "plan_x", "safety": {"decision": "ALLOW"}},
    )
    assert row.mission_id == "mission_test001"

    fetched = mission_store.get_by_id(db, "mission_test001")
    assert fetched is not None
    assert fetched.status == "previewed"
    assert fetched.goal == "test goal"
    assert fetched.plan == {"schema_version": 1, "requested_actions": []}


def test_get_by_id_missing_returns_none(db: Session):
    assert mission_store.get_by_id(db, "does-not-exist") is None


def test_update_status_transitions_and_persists(db: Session):
    mission_store.create(
        db,
        mission_id="mission_test002",
        status="previewed",
        goal="g",
        truth_snapshot_ref="sha256:abc",
        plan=None,
        plan_response=None,
    )
    updated = mission_store.update_status(db, "mission_test002", "approved")
    assert updated is not None
    assert updated.status == "approved"

    refetched = mission_store.get_by_id(db, "mission_test002")
    assert refetched.status == "approved"


def test_update_status_missing_returns_none(db: Session):
    assert mission_store.update_status(db, "nope", "approved") is None


def test_superseded_from_stored(db: Session):
    row = mission_store.create(
        db,
        mission_id="mission_test003",
        status="proposed",
        goal="g2",
        truth_snapshot_ref=None,
        plan=None,
        plan_response=None,
        superseded_from="mission_test001",
    )
    assert row.superseded_from == "mission_test001"


def test_impact_stored_and_retrieved(db: Session):
    row = mission_store.create(
        db,
        mission_id="mission_test004",
        status="previewed",
        goal="g3",
        truth_snapshot_ref="sha256:abc",
        plan=None,
        plan_response=None,
        impact=[{"profile": "agents", "upstream": ["postgres"], "downstream_already_running": [], "available": True, "reason": None}],
    )
    assert row.impact == [
        {"profile": "agents", "upstream": ["postgres"], "downstream_already_running": [], "available": True, "reason": None}
    ]

    fetched = mission_store.get_by_id(db, "mission_test004")
    assert fetched.impact == row.impact
