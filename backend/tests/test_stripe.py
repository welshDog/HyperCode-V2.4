"""
Phase 10G — Stripe Tests (extended from 10F)
Covers: plans, checkout, unknown price, webhook dev mode,
        DB write paths (mocked), cancellation, payment_failed.
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app


# ── Existing 10F tests (kept as-is) ────────────────────────────────

@pytest.mark.asyncio
async def test_get_plans():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/stripe/plans")
    assert resp.status_code == 200
    assert "plans" in resp.json()


@pytest.mark.asyncio
async def test_checkout_creates_session():
    mock_session = MagicMock()
    mock_session.url = "https://checkout.stripe.com/test"
    mock_session.id = "cs_test_123"
    with patch("app.services.stripe_service.stripe.checkout.Session.create", return_value=mock_session):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/api/stripe/checkout", json={"price_id": "starter", "user_id": "user_abc"})
    assert resp.status_code == 200
    data = resp.json()
    assert "checkout_url" in data
    assert "session_id" in data


@pytest.mark.asyncio
async def test_checkout_unknown_price():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/api/stripe/checkout", json={"price_id": ""})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_webhook_dev_mode():
    """Webhook works without STRIPE_WEBHOOK_SECRET (dev mode)."""
    payload = {
        "type": "checkout.session.completed",
        "data": {"object": {
            "id": "cs_test_dev",
            "customer": "cus_test",
            "amount_total": 500,
            "customer_details": {"email": "bro@hyper.com"},
            "metadata": {"user_id": "user_dev", "price_key": "starter"},
        }}
    }
    # Mock DB writes so test doesn’t need a real DB
    with patch("app.services.stripe_service.AsyncSessionLocal") as mock_db_cls:
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)
        mock_db_cls.return_value = mock_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/api/stripe/webhook",
                content=json.dumps(payload),
                headers={"content-type": "application/json"},
            )
    assert resp.status_code == 200
    result = resp.json()
    assert result["event_type"] == "checkout.session.completed"
    assert result["result"]["action"] == "subscription_activated"


# ── Phase 10G — new DB path tests ────────────────────────────────

@pytest.mark.asyncio
async def test_webhook_checkout_returns_tier():
    """checkout.session.completed returns correct tier + token count."""
    from app.services.stripe_service import handle_webhook_event
    import stripe

    event = stripe.Event.construct_from({
        "type": "checkout.session.completed",
        "data": {"object": {
            "id": "cs_test_tier",
            "customer": "cus_abc",
            "amount_total": 3500,
            "customer_details": {"email": "lyndz@hyper.com"},
            "metadata": {"user_id": "user_123", "price_key": "hyper"},
        }}
    }, None)

    with patch("app.services.stripe_service.AsyncSessionLocal") as mock_db_cls:
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)
        mock_db_cls.return_value = mock_db

        result = await handle_webhook_event(event)

    assert result["tier"] == "hyper"
    assert result["tokens_awarded"] == 2500
    assert result["user_id"] == "user_123"


@pytest.mark.asyncio
async def test_webhook_subscription_cancelled():
    """customer.subscription.deleted sets status to cancelled."""
    from app.services.stripe_service import handle_webhook_event
    import stripe

    event = stripe.Event.construct_from({
        "type": "customer.subscription.deleted",
        "data": {"object": {"customer": "cus_cancel_test"}}
    }, None)

    with patch("app.services.stripe_service.AsyncSessionLocal") as mock_db_cls:
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)
        mock_db_cls.return_value = mock_db

        result = await handle_webhook_event(event)

    assert result["action"] == "subscription_cancelled"
    assert result["customer_id"] == "cus_cancel_test"


@pytest.mark.asyncio
async def test_webhook_payment_failed():
    """invoice.payment_failed sets status to past_due."""
    from app.services.stripe_service import handle_webhook_event
    import stripe

    event = stripe.Event.construct_from({
        "type": "invoice.payment_failed",
        "data": {"object": {"customer": "cus_fail_test"}}
    }, None)

    with patch("app.services.stripe_service.AsyncSessionLocal") as mock_db_cls:
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)
        mock_db_cls.return_value = mock_db

        result = await handle_webhook_event(event)

    assert result["action"] == "payment_failed"
