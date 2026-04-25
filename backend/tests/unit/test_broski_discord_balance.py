from datetime import datetime, timedelta, timezone

import pytest

from app.models.models import User
from app.models.broski import BROskiWallet


def test_broski_balance_by_discord_id_returns_404_when_unlinked(client):
    res = client.get("/api/v1/broski/balance/999999999")
    assert res.status_code == 404


def test_broski_balance_by_discord_id_returns_wallet(client, db):
    user = User(
        email="briefing@test.local",
        hashed_password="x",
        discord_id="123456789",
        is_active=True,
        is_superuser=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    wallet = BROskiWallet(
        user_id=user.id,
        coins=4242,
        xp=1337,
        level=4,
        level_name="BROski Recruit",
        last_daily_login=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    db.add(wallet)
    db.commit()

    res = client.get("/api/v1/broski/balance/123456789")
    assert res.status_code == 200
    body = res.json()
    assert body["discord_id"] == "123456789"
    assert body["coins"] == 4242
    assert body["xp"] == 1337
    assert body["daily_claimed"] is True
