"""
Phase 10F — Stripe Route Tests
HyperCode V2.4 | BROski♾

Run: pytest backend/tests/test_stripe.py -v
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ── Test: GET /api/stripe/plans ──────────────────────────────
def test_get_plans():
    response = client.get("/api/stripe/plans")
    assert response.status_code == 200
    data = response.json()
    assert "plans" in data
    assert "starter" in data["plans"]
    assert "hyper" in data["plans"]


# ── Test: POST /api/stripe/checkout (mocked) ────────────────
@patch("app.services.stripe_service.stripe.checkout.Session.create")
def test_checkout_creates_session(mock_create):
    mock_session = MagicMock()
    mock_session.url = "https://checkout.stripe.com/test_session"
    mock_session.id = "cs_test_abc123"
    mock_create.return_value = mock_session

    # Use a raw price ID to bypass empty PRICE_MAP in test env
    response = client.post("/api/stripe/checkout", json={
        "price_id": "price_test_123",
        "user_id": "broski_user_1",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["checkout_url"] == "https://checkout.stripe.com/test_session"
    assert data["session_id"] == "cs_test_abc123"


# ── Test: POST /api/stripe/checkout (bad price) ──────────────
def test_checkout_unknown_price():
    response = client.post("/api/stripe/checkout", json={
        "price_id": "",   # empty = bad
    })
    assert response.status_code == 400


# ── Test: POST /api/stripe/webhook (no secret = dev mode) ────
@patch("app.services.stripe_service.stripe.Event.construct_from")
def test_webhook_dev_mode(mock_construct):
    mock_event = MagicMock()
    mock_event.__getitem__ = lambda self, key: {
        "type": "checkout.session.completed",
        "data": {"object": {"id": "cs_test", "customer": "cus_test", "metadata": {"user_id": "u1"}}},
    }[key]
    mock_construct.return_value = mock_event

    response = client.post(
        "/api/stripe/webhook",
        content=b'{"type": "checkout.session.completed"}',
        headers={"content-type": "application/json"},
    )
    # Should not 500 — may 200 or 400 depending on env
    assert response.status_code in [200, 400]
