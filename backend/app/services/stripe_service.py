"""
Phase 10F — Stripe Service Layer
HyperCode V2.4 | BROski♾ Payment Engine

Handles session creation + webhook event processing.
Keys loaded from environment (set via Docker secrets or .env).
"""
import os
import stripe
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Init Stripe with secret key ──────────────────────────────
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

if not stripe.api_key:
    logger.warning("⚠️  STRIPE_SECRET_KEY not set — Stripe calls will fail!")

# ── Price ID map (friendly name → Stripe price ID) ──────────
# Update these with your real Stripe price IDs from .env
PRICE_MAP: dict[str, str] = {
    "starter":       os.getenv("STRIPE_PRICE_STARTER", ""),
    "builder":       os.getenv("STRIPE_PRICE_BUILDER", ""),
    "hyper":         os.getenv("STRIPE_PRICE_HYPER", ""),
    "pro_monthly":   os.getenv("STRIPE_PRICE_PRO_MONTHLY", ""),
    "pro_yearly":    os.getenv("STRIPE_PRICE_PRO_YEARLY", ""),
    "hyper_monthly": os.getenv("STRIPE_PRICE_HYPER_MONTHLY", ""),
    "hyper_yearly":  os.getenv("STRIPE_PRICE_HYPER_YEARLY", ""),
}


def create_checkout_session(
    price_id: str,
    user_id: Optional[str] = None,
    success_url: str = "http://localhost:3000/success",
    cancel_url: str = "http://localhost:3000/cancel",
) -> stripe.checkout.Session:
    """
    Creates a Stripe Checkout Session for a given price.
    Returns the full session object (use .url to redirect user).
    """
    metadata = {"user_id": user_id} if user_id else {}

    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=cancel_url,
        metadata=metadata,
    )
    logger.info(f"✅ Checkout session created: {session.id} for price {price_id}")
    return session


async def handle_webhook_event(event: stripe.Event) -> dict:
    """
    Process incoming Stripe webhook events.
    Add your business logic per event type below.
    """
    event_type = event["type"]
    data = event["data"]["object"]

    logger.info(f"📨 Stripe webhook received: {event_type}")

    if event_type == "checkout.session.completed":
        user_id = data.get("metadata", {}).get("user_id")
        session_id = data.get("id")
        customer_id = data.get("customer")
        logger.info(f"💰 Payment complete! user={user_id} session={session_id} customer={customer_id}")
        # TODO Phase 10G: update user subscription in DB here
        return {"action": "subscription_activated", "user_id": user_id}

    elif event_type == "customer.subscription.deleted":
        customer_id = data.get("customer")
        logger.info(f"❌ Subscription cancelled: customer={customer_id}")
        # TODO Phase 10G: downgrade user in DB here
        return {"action": "subscription_cancelled", "customer_id": customer_id}

    elif event_type == "invoice.payment_failed":
        customer_id = data.get("customer")
        logger.warning(f"⚠️  Payment failed: customer={customer_id}")
        # TODO Phase 10G: notify user / retry logic here
        return {"action": "payment_failed", "customer_id": customer_id}

    elif event_type == "customer.subscription.updated":
        customer_id = data.get("customer")
        status = data.get("status")
        logger.info(f"🔄 Subscription updated: customer={customer_id} status={status}")
        return {"action": "subscription_updated", "status": status}

    else:
        logger.debug(f"Unhandled event type: {event_type}")
        return {"action": "ignored"}
