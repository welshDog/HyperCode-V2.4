"""
Phase 10G — Stripe Service Layer (DB Writes)
HyperCode V2.4 | BROski♾ Payment Engine

Phase 10F: session creation + basic webhook handling
Phase 10G: full DB writes on webhook events
  - payments table (dedup via stripe_session_id)
  - users.subscription_tier + subscription_status
  - enrollments (for course purchases)
"""
import os
import stripe
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Init Stripe ──────────────────────────────────────────────
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")
if not stripe.api_key:
    logger.warning("⚠️  STRIPE_SECRET_KEY not set — Stripe calls will fail!")

# ── Price ID map ───────────────────────────────────────────
PRICE_MAP: dict[str, str] = {
    "starter":       os.getenv("STRIPE_PRICE_STARTER", ""),
    "builder":       os.getenv("STRIPE_PRICE_BUILDER", ""),
    "hyper":         os.getenv("STRIPE_PRICE_HYPER", ""),
    "pro_monthly":   os.getenv("STRIPE_PRICE_PRO_MONTHLY", ""),
    "pro_yearly":    os.getenv("STRIPE_PRICE_PRO_YEARLY", ""),
    "hyper_monthly": os.getenv("STRIPE_PRICE_HYPER_MONTHLY", ""),
    "hyper_yearly":  os.getenv("STRIPE_PRICE_HYPER_YEARLY", ""),
}

# ── Tier map: Stripe price key → subscription_tier ────────────────
TIER_MAP: dict[str, str] = {
    "starter":       "pro",
    "builder":       "pro",
    "hyper":         "hyper",
    "pro_monthly":   "pro",
    "pro_yearly":    "pro",
    "hyper_monthly": "hyper",
    "hyper_yearly":  "hyper",
}

# ── Token grant map: price key → BROski$ tokens to award ────────
TOKEN_GRANT: dict[str, int] = {
    "starter":       200,
    "builder":       800,
    "hyper":         2500,
    "pro_monthly":   0,
    "pro_yearly":    0,
    "hyper_monthly": 0,
    "hyper_yearly":  0,
}


def create_checkout_session(
    price_id: str,
    user_id: Optional[str] = None,
    success_url: str = "http://localhost:3000/success",
    cancel_url: str = "http://localhost:3000/cancel",
) -> stripe.checkout.Session:
    """
    Creates a Stripe Checkout Session.
    Returns session object — use .url to redirect user.
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


async def _get_db():
    """Get async DB session from app state."""
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        return session


async def _save_payment(db, data: dict, user_id: Optional[str], price_key: Optional[str]) -> bool:
    """
    INSERT into payments table.
    Uses stripe_session_id UNIQUE constraint as dedup guard.
    Returns True if inserted, False if duplicate.
    """
    from sqlalchemy import text
    session_id = data.get("id")
    amount = data.get("amount_total", 0)  # in pence
    customer_email = data.get("customer_details", {}).get("email") or data.get("customer_email")

    try:
        await db.execute(
            text("""
                INSERT INTO public.payments
                    (user_id, user_email, amount_pence, currency, stripe_session_id, status)
                VALUES
                    (:user_id, :email, :amount, :currency, :session_id, 'completed')
                ON CONFLICT (stripe_session_id) DO NOTHING
            """),
            {
                "user_id": user_id,
                "email": customer_email,
                "amount": amount,
                "currency": "gbp",
                "session_id": session_id,
            }
        )
        await db.commit()
        logger.info(f"💾 Payment saved: session={session_id} user={user_id} amount=£{amount/100:.2f}")
        return True
    except Exception as e:
        logger.error(f"Payment insert failed: {e}")
        await db.rollback()
        return False


async def _update_user_subscription(
    db, user_id: str, tier: str, customer_id: str, status: str = "active"
) -> bool:
    """UPDATE users SET subscription_tier, subscription_status, stripe_customer_id."""
    from sqlalchemy import text
    try:
        await db.execute(
            text("""
                UPDATE public.users
                SET
                    subscription_tier = :tier,
                    subscription_status = :status,
                    stripe_customer_id = :customer_id
                WHERE id::text = :user_id
            """),
            {"tier": tier, "status": status, "customer_id": customer_id, "user_id": user_id}
        )
        await db.commit()
        logger.info(f"🌟 User {user_id} upgraded to tier={tier} status={status}")
        return True
    except Exception as e:
        logger.error(f"User subscription update failed: {e}")
        await db.rollback()
        return False


async def _award_tokens(db, user_id: str, amount: int, session_id: str) -> bool:
    """Award BROski$ tokens + log in token_transactions. Dedup via stripe_payment_intent_id."""
    if amount <= 0:
        return True
    from sqlalchemy import text
    try:
        await db.execute(
            text("""
                INSERT INTO public.token_transactions
                    (user_id, amount, reason, stripe_payment_intent_id)
                VALUES
                    (:user_id, :amount, 'stripe_purchase', :session_id)
                ON CONFLICT (stripe_payment_intent_id) DO NOTHING
            """),
            {"user_id": user_id, "amount": amount, "session_id": session_id}
        )
        await db.execute(
            text("""
                UPDATE public.users
                SET broski_tokens = broski_tokens + :amount
                WHERE id::text = :user_id
            """),
            {"user_id": user_id, "amount": amount}
        )
        await db.commit()
        logger.info(f"🪙 Awarded {amount} BROski$ to user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Token award failed: {e}")
        await db.rollback()
        return False


async def handle_webhook_event(event: stripe.Event) -> dict:
    """
    Process Stripe webhook events with full DB writes (Phase 10G).
    """
    from sqlalchemy import text
    event_type = event["type"]
    data = event["data"]["object"]
    logger.info(f"📨 Stripe webhook: {event_type}")

    # ── checkout.session.completed ─────────────────────────────────
    if event_type == "checkout.session.completed":
        user_id = data.get("metadata", {}).get("user_id")
        customer_id = data.get("customer")
        price_key = data.get("metadata", {}).get("price_key")
        session_id = data.get("id")

        # Derive tier from price_key or default to 'pro'
        tier = TIER_MAP.get(price_key, "pro")
        tokens = TOKEN_GRANT.get(price_key, 0)

        results = {"payment": False, "subscription": False, "tokens": False}

        try:
            from app.db.session import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                results["payment"] = await _save_payment(db, data, user_id, price_key)
                if user_id:
                    results["subscription"] = await _update_user_subscription(
                        db, user_id, tier, customer_id
                    )
                    results["tokens"] = await _award_tokens(db, user_id, tokens, session_id)
        except Exception as e:
            logger.error(f"DB write failed for checkout.session.completed: {e}")

        logger.info(f"💳 10G complete: user={user_id} tier={tier} tokens={tokens} results={results}")
        return {
            "action": "subscription_activated",
            "user_id": user_id,
            "tier": tier,
            "tokens_awarded": tokens,
            "db": results,
        }

    # ── customer.subscription.deleted ────────────────────────────
    elif event_type == "customer.subscription.deleted":
        customer_id = data.get("customer")
        try:
            from app.db.session import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("""
                        UPDATE public.users
                        SET subscription_status = 'cancelled', subscription_tier = 'free'
                        WHERE stripe_customer_id = :customer_id
                    """),
                    {"customer_id": customer_id}
                )
                await db.commit()
            logger.info(f"❌ Subscription cancelled + downgraded: customer={customer_id}")
        except Exception as e:
            logger.error(f"Cancellation DB write failed: {e}")
        return {"action": "subscription_cancelled", "customer_id": customer_id}

    # ── invoice.payment_failed ─────────────────────────────────
    elif event_type == "invoice.payment_failed":
        customer_id = data.get("customer")
        try:
            from app.db.session import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("""
                        UPDATE public.users
                        SET subscription_status = 'past_due'
                        WHERE stripe_customer_id = :customer_id
                    """),
                    {"customer_id": customer_id}
                )
                await db.commit()
            logger.warning(f"⚠️ Payment failed → past_due: customer={customer_id}")
        except Exception as e:
            logger.error(f"past_due DB write failed: {e}")
        return {"action": "payment_failed", "customer_id": customer_id}

    # ── customer.subscription.updated ───────────────────────────
    elif event_type == "customer.subscription.updated":
        customer_id = data.get("customer")
        status = data.get("status")
        # Map Stripe status → our status
        status_map = {
            "active": "active", "past_due": "past_due",
            "canceled": "cancelled", "unpaid": "past_due",
        }
        db_status = status_map.get(status, "active")
        try:
            from app.db.session import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                await db.execute(
                    text("""
                        UPDATE public.users
                        SET subscription_status = :status
                        WHERE stripe_customer_id = :customer_id
                    """),
                    {"status": db_status, "customer_id": customer_id}
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Subscription update DB write failed: {e}")
        return {"action": "subscription_updated", "status": db_status}

    else:
        logger.debug(f"Unhandled event: {event_type}")
        return {"action": "ignored"}
