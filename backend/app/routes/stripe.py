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
from app.core.config import settings
from app.services.stripe_service import (
    create_checkout_session,
    create_course_checkout_session,
    handle_webhook_event,
    PRICE_MAP,
)
from app.cache.multi_tier import cache_response
from app.middleware.rate_limiting import limiter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/stripe", tags=["stripe"])


# ── Request schemas ──────────────────────────────────────────
class CheckoutRequest(BaseModel):
    price_id: str                       # "starter" | "builder" | "hyper" | "pro_monthly" |
                                        # "pro_yearly" | "hyper_monthly" | "hyper_yearly" |
                                        # "course_purchase" | raw Stripe price_xxx ID
    user_id: Optional[str] = None
    success_url: Optional[str] = "http://localhost:3000/success"
    cancel_url: Optional[str] = "http://localhost:3000/cancel"
    # Course purchase fields — required when price_id == "course_purchase"
    course_id: Optional[str] = None
    course_title: Optional[str] = None
    price_pence: Optional[int] = None   # GBP pence, e.g. 4900 = £49


# ── POST /api/stripe/checkout ────────────────────────────────
@router.post("/checkout")
@limiter.limit("10/minute")
async def checkout(request: Request, body: CheckoutRequest):
    """
    Create a Stripe Checkout Session.
    Returns a redirect URL for the user to complete payment.

    Two paths:
      - price_id == "course_purchase" → inline price_data session (no Stripe Price ID needed)
      - anything else                 → existing PRICE_MAP lookup (token packs + subscriptions)
    """
    try:
        # ── Course purchase path ─────────────────────────────────────────────
        if body.price_id == "course_purchase":
            if not body.course_id or not body.course_title or body.price_pence is None:
                raise HTTPException(
                    status_code=400,
                    detail="course_id, course_title, and price_pence are required for course_purchase",
                )
            session = create_course_checkout_session(
                course_id=body.course_id,
                course_title=body.course_title,
                price_pence=body.price_pence,
                user_id=body.user_id,
                success_url=body.success_url,
                cancel_url=body.cancel_url,
            )
            return {"checkout_url": session.url, "session_id": session.id}

        # ── Token pack / subscription path ───────────────────────────────────
        price_key = body.price_id
        price_id  = PRICE_MAP.get(price_key, price_key)
        if not price_id:
            raise HTTPException(status_code=400, detail=f"Unknown price_id: {body.price_id}")

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
@limiter.limit("60/minute")
@cache_response("stripe", ttl=60)
async def get_plans(request: Request):
    """Return available plan names mapped to Stripe price IDs."""
    return {"plans": list(PRICE_MAP.keys())}


# ── POST /api/stripe/webhook ─────────────────────────────────
@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
):
    """
    Handle incoming Stripe webhook events.
    Verifies signature using STRIPE_WEBHOOK_SECRET.

    Production: STRIPE_WEBHOOK_SECRET MUST be set — requests are rejected if missing.
    Dev/staging: signature check is skipped with a warning log when secret is absent.
    """
    payload = await request.body()
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    is_production = settings.ENVIRONMENT.lower() == "production"

    if is_production:
        if not webhook_secret:
            raise HTTPException(
                status_code=503,
                detail="STRIPE_WEBHOOK_SECRET not configured — webhook signature verification required in production",
            )
        if not stripe_signature:
            raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")
        try:
            event = stripe.Webhook.construct_event(payload, stripe_signature, webhook_secret)
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Webhook signature failed: {e}")
            raise HTTPException(status_code=400, detail="Invalid signature")
    else:
        if not webhook_secret or not stripe_signature:
            logger.warning("Stripe webhook signature verification disabled (dev mode)")
            try:
                import json

                event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")
        else:
            try:
                event = stripe.Webhook.construct_event(payload, stripe_signature, webhook_secret)
            except stripe.error.SignatureVerificationError as e:
                logger.error(f"Webhook signature failed: {e}")
                raise HTTPException(status_code=400, detail="Invalid signature")

    result = await handle_webhook_event(event)
    return {"status": "ok", "event_type": event["type"], "result": result}
