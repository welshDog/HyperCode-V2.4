import pytest
from unittest.mock import AsyncMock, patch

from app.core import security
from app.core.config import settings
from app.models import models


def _make_user(db):
    user = models.User(
        email="mission-tester@example.com",
        hashed_password="x",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _auth_headers(user):
    from jose import jwt

    # NOTE: settings.JWT_AUDIENCE / settings.JWT_ISSUER default to None in
    # this repo (no .env in tests). app.api.deps.get_current_user calls
    # jwt.decode(..., audience=settings.JWT_AUDIENCE, issuer=settings.JWT_ISSUER).
    # python-jose treats an "aud"/"iss" claim present-but-None in the token
    # as a validation failure (JWTClaimsError: "Invalid claim format in
    # token") rather than skipping validation -- so those claims must be
    # OMITTED entirely, not set to None. This matches the existing
    # `_make_token` helper in backend/tests/unit/test_deps.py, which mints
    # tokens with only a "sub" claim for the same dependency.
    token = jwt.encode({"sub": str(user.id)}, settings.JWT_SECRET, algorithm=security.ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


class _MockResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("http error")

    def json(self):
        return self._payload


def test_propose_requires_auth(client):
    resp = client.post("/api/v1/missions/propose", json={"goal": "do the thing"})
    assert resp.status_code in (401, 403)


def test_propose_persists_and_returns_previewed(client, db):
    user = _make_user(db)
    mock_payload = {
        "schema_version": 1,
        "mission_id": "mission_mocked01",
        "goal": "do the thing",
        "truth_snapshot_ref": "sha256:abc",
        "rationale": "because",
        "plan": {"schema_version": 1, "mission_id": "mission_mocked01", "requested_actions": []},
        "plan_response": {
            "plan_id": "plan_x",
            "plan_hash": "sha256:x",
            "safety": {"decision": "ESCALATE", "reason": "r", "shepherd_available": True},
            "execution": {"performed": False, "would_execute": []},
        },
        "status": "previewed",
        "superseded_from": None,
    }
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=_MockResponse(mock_payload))):
        resp = client.post(
            "/api/v1/missions/propose",
            json={"goal": "do the thing"},
            headers=_auth_headers(user),
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "previewed"
    assert body["plan_response"]["execution"]["performed"] is False


def test_propose_returns_preview_unavailable_when_mission_director_unreachable(client, db):
    user = _make_user(db)
    with patch("httpx.AsyncClient.post", new=AsyncMock(side_effect=RuntimeError("connection refused"))):
        resp = client.post(
            "/api/v1/missions/propose",
            json={"goal": "do the thing"},
            headers=_auth_headers(user),
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "preview_unavailable"


def test_propose_returns_preview_unavailable_when_mission_director_response_malformed(client, db):
    user = _make_user(db)
    # 200 + valid JSON, but missing required fields (e.g. no "mission_id") --
    # distinct from a network failure or a non-200 status, which the other
    # two propose tests already cover.
    malformed_payload = {"status": "previewed"}
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=_MockResponse(malformed_payload))):
        resp = client.post(
            "/api/v1/missions/propose",
            json={"goal": "do the thing"},
            headers=_auth_headers(user),
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "preview_unavailable"


def test_propose_returns_preview_unavailable_when_status_spoofed_approved(client, db):
    user = _make_user(db)
    # /v1/plan's create_plan route can only ever set "previewed",
    # "preview_unavailable", or "rejected_malformed" -- "approved" is a
    # status the real route never produces, so a response claiming it must
    # be treated as untrusted/malformed, not persisted verbatim (that would
    # let a buggy or spoofed mission-director bypass human review entirely).
    spoofed_payload = {
        "schema_version": 1,
        "mission_id": "mission_spoofed01",
        "goal": "do the thing",
        "truth_snapshot_ref": "sha256:abc",
        "rationale": "because",
        "plan": None,
        "plan_response": None,
        "status": "approved",
        "superseded_from": None,
    }
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=_MockResponse(spoofed_payload))):
        resp = client.post(
            "/api/v1/missions/propose",
            json={"goal": "do the thing"},
            headers=_auth_headers(user),
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "preview_unavailable"
    # also proves the locally-generated mission_id wins over the echoed one
    assert body["mission_id"] != "mission_spoofed01"


def test_review_requires_auth(client):
    resp = client.post("/api/v1/missions/mission_x/review", json={"decision": "approve"})
    assert resp.status_code in (401, 403)


def test_review_404_on_unknown_mission(client, db):
    user = _make_user(db)
    resp = client.post(
        "/api/v1/missions/does-not-exist/review",
        json={"decision": "approve"},
        headers=_auth_headers(user),
    )
    assert resp.status_code == 404


def test_review_409_when_status_not_previewed(client, db):
    user = _make_user(db)
    from app.services import mission_store

    mission_store.create(
        db,
        mission_id="mission_notprevd",
        status="rejected_malformed",
        goal="g",
        truth_snapshot_ref=None,
        plan=None,
        plan_response=None,
    )
    resp = client.post(
        "/api/v1/missions/mission_notprevd/review",
        json={"decision": "approve"},
        headers=_auth_headers(user),
    )
    assert resp.status_code == 409


def test_review_rejects_approval_when_safety_decision_is_block(client, db):
    user = _make_user(db)
    from app.services import mission_store

    mission_store.create(
        db,
        mission_id="mission_blocked",
        status="previewed",
        goal="g",
        truth_snapshot_ref="sha256:abc",
        plan=None,
        plan_response={
            "plan_id": "plan_x",
            "plan_hash": "sha256:x",
            "safety": {"decision": "BLOCK", "reason": "r", "shepherd_available": True},
            "execution": {"performed": False, "would_execute": []},
        },
    )
    resp = client.post(
        "/api/v1/missions/mission_blocked/review",
        json={"decision": "approve"},
        headers=_auth_headers(user),
    )
    assert resp.status_code == 409

    from app.services import mission_store as ms

    assert ms.get_by_id(db, "mission_blocked").status == "previewed"


def test_review_allows_reject_even_when_safety_decision_is_block(client, db):
    user = _make_user(db)
    from app.services import mission_store

    mission_store.create(
        db,
        mission_id="mission_blocked_reject",
        status="previewed",
        goal="g",
        truth_snapshot_ref="sha256:abc",
        plan=None,
        plan_response={
            "plan_id": "plan_x",
            "plan_hash": "sha256:x",
            "safety": {"decision": "BLOCK", "reason": "r", "shepherd_available": False},
            "execution": {"performed": False, "would_execute": []},
        },
    )
    resp = client.post(
        "/api/v1/missions/mission_blocked_reject/review",
        json={"decision": "reject"},
        headers=_auth_headers(user),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"


def test_review_requires_escalation_reason_when_safety_decision_is_escalate(client, db):
    user = _make_user(db)
    from app.services import mission_store

    mission_store.create(
        db,
        mission_id="mission_escalate",
        status="previewed",
        goal="g",
        truth_snapshot_ref="sha256:abc",
        plan=None,
        plan_response={
            "plan_id": "plan_x",
            "plan_hash": "sha256:x",
            "safety": {"decision": "ESCALATE", "reason": "r", "shepherd_available": True},
            "execution": {"performed": False, "would_execute": []},
        },
    )
    resp = client.post(
        "/api/v1/missions/mission_escalate/review",
        json={"decision": "approve"},
        headers=_auth_headers(user),
    )
    assert resp.status_code == 422


def test_review_approves_escalate_when_reason_given_and_logs_it(client, db):
    user = _make_user(db)
    from app.services import mission_store

    mission_store.create(
        db,
        mission_id="mission_escalate_ok",
        status="previewed",
        goal="g",
        truth_snapshot_ref="sha256:abc",
        plan=None,
        plan_response={
            "plan_id": "plan_x",
            "plan_hash": "sha256:x",
            "safety": {"decision": "ESCALATE", "reason": "r", "shepherd_available": True},
            "execution": {"performed": False, "would_execute": []},
        },
    )
    resp = client.post(
        "/api/v1/missions/mission_escalate_ok/review",
        json={"decision": "approve", "escalation_reason": "reviewed by Bro, acceptable risk"},
        headers=_auth_headers(user),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    from app.models.governance import GovernanceLedger

    rows = db.query(GovernanceLedger).filter(GovernanceLedger.action == "mission.review").all()
    matches = [r for r in rows if r.payload.get("mission_id") == "mission_escalate_ok"]
    assert len(matches) == 1
    assert matches[0].payload["escalation_reason"] == "reviewed by Bro, acceptable risk"


def test_review_approve_transitions_and_writes_ledger(client, db):
    user = _make_user(db)
    from app.services import mission_store

    mission_store.create(
        db,
        mission_id="mission_toreview",
        status="previewed",
        goal="g",
        truth_snapshot_ref="sha256:abc",
        plan=None,
        plan_response=None,
    )
    resp = client.post(
        "/api/v1/missions/mission_toreview/review",
        json={"decision": "approve"},
        headers=_auth_headers(user),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    from app.models.governance import GovernanceLedger

    ledger_rows = (
        db.query(GovernanceLedger).filter(GovernanceLedger.action == "mission.review").all()
    )
    assert len(ledger_rows) == 1
    assert ledger_rows[0].decision == "approved"


def test_propose_persists_and_returns_impact(client, db):
    user = _make_user(db)
    mock_payload = {
        "schema_version": 1,
        "mission_id": "mission_mocked_impact",
        "goal": "do the thing",
        "truth_snapshot_ref": "sha256:abc",
        "rationale": "because",
        "plan": {"schema_version": 1, "mission_id": "mission_mocked_impact", "requested_actions": []},
        "plan_response": {
            "plan_id": "plan_x",
            "plan_hash": "sha256:x",
            "safety": {"decision": "ESCALATE", "reason": "r", "shepherd_available": True},
            "execution": {"performed": False, "would_execute": []},
        },
        "impact": [
            {"profile": "agents", "upstream": ["postgres"], "downstream_already_running": [], "available": True, "reason": None}
        ],
        "status": "previewed",
        "superseded_from": None,
    }
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=_MockResponse(mock_payload))):
        resp = client.post(
            "/api/v1/missions/propose",
            json={"goal": "do the thing"},
            headers=_auth_headers(user),
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["impact"] == mock_payload["impact"]
