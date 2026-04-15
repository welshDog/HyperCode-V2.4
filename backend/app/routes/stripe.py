"""
Phase 10F — Stripe Checkout & Webhook Routes
HyperCode V2.4 | BROski♾ Payment Engine
"""
import os
import stripe
import logging
from fastapi import APIRouter, HTTPException, Request, Header
from pydantic import BaseModel
from typing import Optional
from app.services.stripe_service import (
    create_checkout_session,
    handle_webhook_event,
    PRICE_MAP,
)
from app.cache.multi_tier import cache_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stripe", tags=["stripe"])


# ── Request schemas ──────────────────────────────────────────
class CheckoutRequest(BaseModel):
    price_id: str          # e.g. "starter", "builder", "hyper" OR a raw price_xxx ID
    user_id: Optional[str] = None
    success_url: Optional[str] = "http://localhost:3000/success"
    cancel_url: Optional[str] = "http://localhost:3000/cancel"


# ── POST /api/stripe/checkout ────────────────────────────────
@router.post("/checkout")
async def checkout(body: CheckoutRequest):
    """
    Create a Stripe Checkout Session.
    Returns a redirect URL for the user to complete payment.
    """
    # Resolve friendly name to Stripe price ID
    price_key = body.price_id                          # friendly key e.g. "starter"
    price_id  = PRICE_MAP.get(price_key, price_key)   # raw Stripe price_xxx ID
    if not price_id:
        raise HTTPException(status_code=400, detail=f"Unknown price_id: {body.price_id}")

    try:
        session = create_checkout_session(
            price_id=price_id,
            price_key=price_key,
            user_id=body.user_id,
            success_url=body.success_url,
            cancel_url=body.cancel_url,
        )
        return {"checkout_url": session.url, "session_id": session.id}
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ── GET /api/stripe/plans ────────────────────────────────────
@router.get("/plans")
@cache_response("stripe", ttl=60)
async def get_plans():
    """Return available plan names mapped to Stripe price IDs."""
    return {"plans": list(PRICE_MAP.keys())}


# ── POST /api/stripe/webhook ─────────────────────────────────
@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None),
):
    """
    Handle incoming Stripe webhook events.
    Verifies signature using STRIPE_WEBHOOK_SECRET.
    """
    payload = await request.body()
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    if not webhook_secret:
        logger.warning("STRIPE_WEBHOOK_SECRET not set — skipping signature check (dev mode)")
        try:
            import json
            event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")
    else:
        try:
            event = stripe.Webhook.construct_event(
                payload, stripe_signature, webhook_secret
            )
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Webhook signature failed: {e}")
            raise HTTPException(status_code=400, detail="Invalid signature")

    result = await handle_webhook_event(event)
    return {"status": "ok", "event_type": event["type"], "result": result}
