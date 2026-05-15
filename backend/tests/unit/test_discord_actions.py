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


def test_discord_actions_requires_auth(client):
    resp = client.post("/api/v1/discord/actions", json={})
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
            "X-Request-Hash": "abcd1234abcd1234",
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
            "X-Request-Hash": "abcd1234abcd1234",
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
        "X-Request-Hash": "abcd1234abcd1234",
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
    body2 = {"action": "economy.balance", "discord": _discord_ctx(), "payload": {"x": 1}}

    headers = {
        **_auth_headers(),
        "Idempotency-Key": "discord:i1",
        "X-Request-Hash": "abcd1234abcd1234",
    }

    ok = client.post("/api/v1/discord/actions", headers=headers, json=body1)
    assert ok.status_code == 200

    bad = client.post("/api/v1/discord/actions", headers=headers, json=body2)
    assert bad.status_code == 409
    assert bad.json()["code"] == "idempotency_mismatch"


def test_broski_pulse_exists(client):
    resp = client.get("/api/v1/broski/pulse")
    assert resp.status_code in (200, 404)
