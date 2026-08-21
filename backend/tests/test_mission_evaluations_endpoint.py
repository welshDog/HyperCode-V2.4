from jose import jwt

from app.core import security
from app.core.config import settings
from app.models import models
from app.models.mission import MissionProposal


def _make_user(db):
    user = models.User(
        email="evaluator-tester@example.com",
        hashed_password="x",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _auth_headers(user):
    token = jwt.encode({"sub": str(user.id)}, settings.JWT_SECRET, algorithm=security.ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


def _seed_proposal(db, mission_id, status, plan_response=None):
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


def test_run_requires_auth(client):
    resp = client.post("/api/v1/mission-evaluations/run")
    assert resp.status_code in (401, 403)


def test_list_requires_auth(client):
    resp = client.get("/api/v1/mission-evaluations")
    assert resp.status_code in (401, 403)


def test_summary_requires_auth(client):
    resp = client.get("/api/v1/mission-evaluations/summary")
    assert resp.status_code in (401, 403)


def test_run_evaluates_seeded_terminal_mission(client, db):
    user = _make_user(db)
    _seed_proposal(db, "mission_ep1", "rejected_malformed")

    resp = client.post("/api/v1/mission-evaluations/run", headers=_auth_headers(user))
    assert resp.status_code == 200
    body = resp.json()
    assert body["evaluated_count"] == 1
    assert body["anomaly_count"] == 0


def test_run_flags_flagship_anomaly_end_to_end(client, db):
    user = _make_user(db)
    # Mint the auth header once and reuse it for both calls below: the store's
    # run_evaluation() commits on this test's shared `db` session
    # (expire_on_commit=True by default), and conftest.py's override_get_db
    # closes that same session after the request completes -- so a second
    # `_auth_headers(user)` call after the first client.post() would touch an
    # expired, detached ORM instance (DetachedInstanceError). Same token both
    # times is semantically identical since it's the same user's id either way.
    headers = _auth_headers(user)
    _seed_proposal(
        db,
        "mission_ep2",
        "approved",
        plan_response={"safety": {"decision": "BLOCK", "shepherd_available": True}},
    )

    resp = client.post("/api/v1/mission-evaluations/run", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["anomaly_count"] == 1

    list_resp = client.get(
        "/api/v1/mission-evaluations?verdict=anomaly", headers=headers
    )
    assert list_resp.status_code == 200
    rows = list_resp.json()["rows"]
    assert len(rows) == 1
    assert rows[0]["mission_id"] == "mission_ep2"
    assert rows[0]["checks"]["anomaly_approved_despite_block"] is True


def test_summary_endpoint_returns_rollup(client, db):
    user = _make_user(db)
    # Same reuse-the-header rationale as test_run_flags_flagship_anomaly_end_to_end above.
    headers = _auth_headers(user)
    _seed_proposal(db, "mission_ep3", "preview_unavailable")
    client.post("/api/v1/mission-evaluations/run", headers=headers)

    resp = client.get("/api/v1/mission-evaluations/summary", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_evaluated"] == 1
    assert body["preview_failed_rate"] == 1.0
