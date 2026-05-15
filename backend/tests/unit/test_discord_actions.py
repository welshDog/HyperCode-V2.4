import hashlib
import json

import pytest

from app.core.config import settings
from app.models import models


def _auth_headers() -> dict[str, str]:
    return {"Authorization": "Bearer test-bot-key"}


def _discord_ctx(*, interaction_id: str = "i1") -> dict:
    return {
        "user_id": "u1",
        "guild_id": "g1",
        "channel_id": "c1",
        "interaction_id": interaction_id,
    }


def _req_hash(body: dict) -> str:
    raw = json.dumps(body, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def test_discord_actions_requires_auth(client):
    body = {"action": "economy.balance", "discord": _discord_ctx(), "payload": {}}
    resp = client.post(
        "/api/v1/discord/actions",
        headers={
            "Idempotency-Key": "discord:i1",
            "X-Request-Hash": _req_hash(body),
        },
        json=body,
    )
    assert resp.status_code in (401, 403)


def test_discord_actions_daily_claim_happy_path(client, db, monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "test-bot-key", raising=True)

    user = models.User(
        email="a@example.com",
        hashed_password="x",
        discord_id="u1",
        is_active=True,
    )
    db.add(user)
    db.commit()

    body = {"action": "daily.claim", "discord": _discord_ctx(), "payload": {}}
    resp = client.post(
        "/api/v1/discord/actions",
        headers={
            **_auth_headers(),
            "Idempotency-Key": "discord:i1",
            "X-Request-Hash": _req_hash(body),
        },
        json=body,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["render"]["type"] == "embed"


def test_discord_actions_balance_happy_path(client, db, monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "test-bot-key", raising=True)

    user = models.User(
        email="b@example.com",
        hashed_password="x",
        discord_id="u1",
        is_active=True,
    )
    db.add(user)
    db.commit()

    body = {"action": "economy.balance", "discord": _discord_ctx(), "payload": {}}
    resp = client.post(
        "/api/v1/discord/actions",
        headers={
            **_auth_headers(),
            "Idempotency-Key": "discord:i1",
            "X-Request-Hash": _req_hash(body),
        },
        json=body,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["render"]["type"] == "embed"


def test_discord_actions_member_join_not_linked_returns_200(client, monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "test-bot-key", raising=True)

    body = {
        "action": "member.join",
        "discord": _discord_ctx(interaction_id="join_1"),
        "payload": {},
    }
    resp = client.post(
        "/api/v1/discord/actions",
        headers={
            **_auth_headers(),
            "Idempotency-Key": "discord:join_1",
            "X-Request-Hash": _req_hash(body),
        },
        json=body,
    )
    assert resp.status_code == 200
    assert resp.json()["render"]["type"] == "embed"


def test_discord_actions_give_happy_path(client, db, monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "test-bot-key", raising=True)

    sender = models.User(
        email="s@example.com",
        hashed_password="x",
        discord_id="u1",
        is_active=True,
    )
    recipient = models.User(
        email="r@example.com",
        hashed_password="x",
        discord_id="u2",
        is_active=True,
    )
    db.add(sender)
    db.add(recipient)
    db.commit()

    from app.services import broski_service

    broski_service.award_coins(sender.id, 25, "seed", db)

    body = {
        "action": "economy.give",
        "discord": _discord_ctx(),
        "payload": {"to_discord_id": "u2", "amount": 10},
    }
    resp = client.post(
        "/api/v1/discord/actions",
        headers={
            **_auth_headers(),
            "Idempotency-Key": "discord:i1",
            "X-Request-Hash": _req_hash(body),
        },
        json=body,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["render"]["type"] == "embed"


def test_discord_actions_idempotency_returns_409(client, db, monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "test-bot-key", raising=True)

    user = models.User(
        email="c@example.com",
        hashed_password="x",
        discord_id="u1",
        is_active=True,
    )
    db.add(user)
    db.commit()

    body = {"action": "daily.claim", "discord": _discord_ctx(), "payload": {}}
    headers = {
        **_auth_headers(),
        "Idempotency-Key": "discord:i1",
        "X-Request-Hash": _req_hash(body),
    }

    first = client.post("/api/v1/discord/actions", headers=headers, json=body)
    assert first.status_code == 200

    second = client.post("/api/v1/discord/actions", headers=headers, json=body)
    assert second.status_code == 409
    assert second.json() == first.json()


def test_discord_actions_rejects_hash_mismatch(client, db, monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "test-bot-key", raising=True)

    user = models.User(
        email="d@example.com",
        hashed_password="x",
        discord_id="u1",
        is_active=True,
    )
    db.add(user)
    db.commit()

    body1 = {"action": "economy.balance", "discord": _discord_ctx(), "payload": {}}
    ok = client.post(
        "/api/v1/discord/actions",
        headers={
            **_auth_headers(),
            "Idempotency-Key": "discord:i1",
            "X-Request-Hash": _req_hash(body1),
        },
        json=body1,
    )
    assert ok.status_code == 200

    body2 = {"action": "economy.balance", "discord": _discord_ctx(), "payload": {"x": 1}}
    bad = client.post(
        "/api/v1/discord/actions",
        headers={
            **_auth_headers(),
            "Idempotency-Key": "discord:i1",
            "X-Request-Hash": _req_hash(body2),
        },
        json=body2,
    )
    assert bad.status_code == 409
    assert bad.json()["code"] == "idempotency_mismatch"


def test_broski_pulse_exists(client):
    resp = client.get("/api/v1/broski/pulse")
    assert resp.status_code in (200, 404)


def test_discord_actions_ai_ask_returns_embed(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "API_KEY", "test-bot-key", raising=True)
    monkeypatch.setattr(settings, "ORCHESTRATOR_URL", "http://orch", raising=True)
    monkeypatch.setattr(settings, "ORCHESTRATOR_API_KEY", "ok", raising=True)

    class _Resp:
        status_code = 200

        def json(self):
            return {"status": "completed", "result": {"message": "hi"}}

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, json=None, headers=None):
            return _Resp()

    import app.api.v1.endpoints.discord_actions as mod

    monkeypatch.setattr(mod.httpx, "Client", _Client)

    body = {"action": "ai.ask", "discord": _discord_ctx(), "payload": {"question": "yo"}}
    resp = client.post(
        "/api/v1/discord/actions",
        headers={
            **_auth_headers(),
            "Idempotency-Key": "discord:i1",
            "X-Request-Hash": _req_hash(body),
        },
        json=body,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["render"]["type"] == "embed"


def test_discord_actions_ai_chat_missing_text_is_ok(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "API_KEY", "test-bot-key", raising=True)
    monkeypatch.setattr(settings, "ORCHESTRATOR_URL", "http://orch", raising=True)
    monkeypatch.setattr(settings, "ORCHESTRATOR_API_KEY", "ok", raising=True)

    body = {"action": "ai.chat", "discord": _discord_ctx(), "payload": {}}
    resp = client.post(
        "/api/v1/discord/actions",
        headers={
            **_auth_headers(),
            "Idempotency-Key": "discord:i1",
            "X-Request-Hash": _req_hash(body),
        },
        json=body,
    )
    assert resp.status_code == 200
    assert resp.json()["render"]["type"] == "embed"


def test_focus_start_is_idempotent_returns_existing_session(client, db, monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "test-bot-key", raising=True)

    user = models.User(
        email="focus@example.com",
        hashed_password="x",
        discord_id="u1",
        is_active=True,
    )
    db.add(user)
    db.commit()

    body1 = {"action": "focus.start", "discord": _discord_ctx(), "payload": {}}
    r1 = client.post(
        "/api/v1/discord/actions",
        headers={
            **_auth_headers(),
            "Idempotency-Key": "discord:fs1",
            "X-Request-Hash": _req_hash(body1),
        },
        json=body1,
    )
    assert r1.status_code == 200
    s1 = r1.json()["data"]["session_id"]

    body2 = {"action": "focus.start", "discord": _discord_ctx(interaction_id="fs2"), "payload": {}}
    r2 = client.post(
        "/api/v1/discord/actions",
        headers={
            **_auth_headers(),
            "Idempotency-Key": "discord:fs2",
            "X-Request-Hash": _req_hash(body2),
        },
        json=body2,
    )
    assert r2.status_code == 200
    assert r2.json()["data"]["session_id"] == s1


def test_focus_stop_baseline_not_ready_returns_no_delta(client, db, monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "test-bot-key", raising=True)

    user = models.User(
        email="focus2@example.com",
        hashed_password="x",
        discord_id="u1",
        is_active=True,
    )
    db.add(user)
    db.commit()

    start = {"action": "focus.start", "discord": _discord_ctx(), "payload": {}}
    r1 = client.post(
        "/api/v1/discord/actions",
        headers={
            **_auth_headers(),
            "Idempotency-Key": "discord:fs3",
            "X-Request-Hash": _req_hash(start),
        },
        json=start,
    )
    assert r1.status_code == 200

    from app.models.broski import FocusSession

    sess = (
        db.query(FocusSession)
        .filter(FocusSession.discord_id == "u1", FocusSession.ended_at.is_(None))
        .first()
    )
    assert sess is not None
    sess.started_at = sess.started_at.replace(year=sess.started_at.year - 1)
    db.commit()

    stop = {"action": "focus.stop", "discord": _discord_ctx(interaction_id="fs4"), "payload": {}}
    r2 = client.post(
        "/api/v1/discord/actions",
        headers={
            **_auth_headers(),
            "Idempotency-Key": "discord:fs4",
            "X-Request-Hash": _req_hash(stop),
        },
        json=stop,
    )
    assert r2.status_code == 200
    data = r2.json()["data"]
    assert data["delta_available"] is False
    assert data["coins_awarded"] == 0


def test_focus_reward_calc_delta_counts_to_coins(client, db, monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "test-bot-key", raising=True)
    monkeypatch.setattr(settings, "FOCUS_MIN_MINUTES", 5, raising=False)

    user = models.User(
        email="focus3@example.com",
        hashed_password="x",
        discord_id="u1",
        is_active=True,
    )
    db.add(user)
    db.commit()

    start = {"action": "focus.start", "discord": _discord_ctx(), "payload": {}}
    r1 = client.post(
        "/api/v1/discord/actions",
        headers={
            **_auth_headers(),
            "Idempotency-Key": "discord:fs5",
            "X-Request-Hash": _req_hash(start),
        },
        json=start,
    )
    assert r1.status_code == 200

    from app.models.broski import FocusSession

    sess = (
        db.query(FocusSession)
        .filter(FocusSession.discord_id == "u1", FocusSession.ended_at.is_(None))
        .first()
    )
    assert sess is not None
    sess.started_at = sess.started_at.replace(year=sess.started_at.year - 1)
    sess.baseline_ready = True
    sess.baseline_score = 90
    sess.baseline_grade = "A"
    sess.baseline_counts = {"critical": 1, "high": 2, "medium": 3, "low": 0}
    db.commit()

    class _Resp:
        status_code = 200

        def json(self):
            return {
                "scan_id": "x",
                "persisted": True,
                "score": 95,
                "grade": "A",
                "counts": {"critical": 0, "high": 0, "medium": 0, "low": 0},
                "total_files": 10,
                "top_issues": [],
                "scanned_at": "2026-05-15T00:00:00Z",
                "scan_targets": ["backend"],
            }

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, json=None, headers=None, params=None):
            return _Resp()

    import app.api.v1.endpoints.discord_actions as mod

    monkeypatch.setattr(mod.httpx, "Client", _Client)

    stop = {"action": "focus.stop", "discord": _discord_ctx(interaction_id="fs6"), "payload": {}}
    r2 = client.post(
        "/api/v1/discord/actions",
        headers={
            **_auth_headers(),
            "Idempotency-Key": "discord:fs6",
            "X-Request-Hash": _req_hash(stop),
        },
        json=stop,
    )
    assert r2.status_code == 200
    assert r2.json()["data"]["coins_awarded"] == 190


def test_focus_stop_idempotent_by_idempotency_key(client, db, monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "test-bot-key", raising=True)

    user = models.User(
        email="focus4@example.com",
        hashed_password="x",
        discord_id="u1",
        is_active=True,
    )
    db.add(user)
    db.commit()

    start = {"action": "focus.start", "discord": _discord_ctx(), "payload": {}}
    r1 = client.post(
        "/api/v1/discord/actions",
        headers={
            **_auth_headers(),
            "Idempotency-Key": "discord:fs7",
            "X-Request-Hash": _req_hash(start),
        },
        json=start,
    )
    assert r1.status_code == 200

    stop = {"action": "focus.stop", "discord": _discord_ctx(interaction_id="fs8"), "payload": {}}
    headers = {
        **_auth_headers(),
        "Idempotency-Key": "discord:fs8",
        "X-Request-Hash": _req_hash(stop),
    }
    first = client.post("/api/v1/discord/actions", headers=headers, json=stop)
    assert first.status_code == 200

    second = client.post("/api/v1/discord/actions", headers=headers, json=stop)
    assert second.status_code == 409
    assert second.json() == first.json()


def test_missions_today_not_claimable_without_qualifying_focus(client, db, monkeypatch):
    monkeypatch.setattr(settings, "API_KEY", "test-bot-key", raising=True)

    user = models.User(
        email="m1@example.com",
        hashed_password="x",
        discord_id="u1",
        is_active=True,
    )
    db.add(user)
    db.commit()

    body = {"action": "missions.today", "discord": _discord_ctx(), "payload": {}}
    resp = client.post(
        "/api/v1/discord/actions",
        headers={
            **_auth_headers(),
            "Idempotency-Key": "discord:mt1",
            "X-Request-Hash": _req_hash(body),
        },
        json=body,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["focus_block"]["claimable"] is False


def test_missions_today_claimable_with_qualifying_focus(client, db, monkeypatch):
    from datetime import datetime, timezone

    monkeypatch.setattr(settings, "API_KEY", "test-bot-key", raising=True)

    user = models.User(
        email="m2@example.com",
        hashed_password="x",
        discord_id="u1",
        is_active=True,
    )
    db.add(user)
    db.commit()

    from app.models.broski import FocusSession

    s = FocusSession(
        user_id=user.id,
        discord_id="u1",
        started_at=datetime.now(timezone.utc),
        ended_at=datetime.now(timezone.utc),
        minutes=int(settings.FOCUS_MIN_MINUTES),
        baseline_ready=False,
        delta_available=False,
        coins_awarded=0,
    )
    db.add(s)
    db.commit()

    body = {"action": "missions.today", "discord": _discord_ctx(), "payload": {}}
    resp = client.post(
        "/api/v1/discord/actions",
        headers={
            **_auth_headers(),
            "Idempotency-Key": "discord:mt2",
            "X-Request-Hash": _req_hash(body),
        },
        json=body,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["focus_block"]["claimable"] is True


def test_missions_claim_awards_once(client, db, monkeypatch):
    from datetime import datetime, timezone

    monkeypatch.setattr(settings, "API_KEY", "test-bot-key", raising=True)

    user = models.User(
        email="m3@example.com",
        hashed_password="x",
        discord_id="u1",
        is_active=True,
    )
    db.add(user)
    db.commit()

    from app.models.broski import FocusSession

    s = FocusSession(
        user_id=user.id,
        discord_id="u1",
        started_at=datetime.now(timezone.utc),
        ended_at=datetime.now(timezone.utc),
        minutes=int(settings.FOCUS_MIN_MINUTES),
        baseline_ready=False,
        delta_available=False,
        coins_awarded=0,
    )
    db.add(s)
    db.commit()

    claim = {"action": "missions.claim", "discord": _discord_ctx(), "payload": {"slug": "focus_block"}}
    headers = {
        **_auth_headers(),
        "Idempotency-Key": "discord:mc1",
        "X-Request-Hash": _req_hash(claim),
    }
    first = client.post("/api/v1/discord/actions", headers=headers, json=claim)
    assert first.status_code == 200
    assert first.json()["data"]["awarded"] is True

    second = client.post(
        "/api/v1/discord/actions",
        headers={
            **_auth_headers(),
            "Idempotency-Key": "discord:mc2",
            "X-Request-Hash": _req_hash(claim),
        },
        json=claim,
    )
    assert second.status_code == 200
    assert second.json()["data"]["awarded"] is False


def test_missions_claim_idempotent_by_idempotency_key(client, db, monkeypatch):
    from datetime import datetime, timezone

    monkeypatch.setattr(settings, "API_KEY", "test-bot-key", raising=True)

    user = models.User(
        email="m4@example.com",
        hashed_password="x",
        discord_id="u1",
        is_active=True,
    )
    db.add(user)
    db.commit()

    from app.models.broski import FocusSession

    s = FocusSession(
        user_id=user.id,
        discord_id="u1",
        started_at=datetime.now(timezone.utc),
        ended_at=datetime.now(timezone.utc),
        minutes=int(settings.FOCUS_MIN_MINUTES),
        baseline_ready=False,
        delta_available=False,
        coins_awarded=0,
    )
    db.add(s)
    db.commit()

    claim = {"action": "missions.claim", "discord": _discord_ctx(interaction_id="mci1"), "payload": {"slug": "focus_block"}}
    headers = {
        **_auth_headers(),
        "Idempotency-Key": "discord:mci1",
        "X-Request-Hash": _req_hash(claim),
    }
    first = client.post("/api/v1/discord/actions", headers=headers, json=claim)
    assert first.status_code == 200

    second = client.post("/api/v1/discord/actions", headers=headers, json=claim)
    assert second.status_code == 409
    assert second.json() == first.json()
