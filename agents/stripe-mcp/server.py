"""
Stripe MCP Server

Exposes Stripe checkout, webhooks, and subscriptions as MCP tools and resources.

Tools:
  - create_checkout(price_id, user_id)
  - handle_webhook_event(payload, sig_header)
  - get_subscription(user_id)

Resources:
  - stripe://subscription/{user_id}
  - stripe://plans
"""

import os
import json
import stripe
from typing import Optional
from contextlib import asynccontextmanager

import asyncio
from asyncpg import create_pool, Pool
from fastapi import FastAPI, Request, HTTPException
import uvicorn

# ---------- Config ----------

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
DATABASE_URL = os.environ.get("DATABASE_URL")

if not STRIPE_SECRET_KEY:
    raise RuntimeError("STRIPE_SECRET_KEY env var must be set")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL env var must be set")

stripe.api_key = STRIPE_SECRET_KEY

# Price map (mirrors stripe_service.py)
PRICE_MAP = {
    "starter": "STRIPE_PRICE_STARTER",
    "builder": "STRIPE_PRICE_BUILDER",
    "hyper": "STRIPE_PRICE_HYPER",
    "pro_monthly": "STRIPE_PRICE_PRO_MONTHLY",
    "pro_yearly": "STRIPE_PRICE_PRO_YEARLY",
    "hyper_monthly": "STRIPE_PRICE_HYPER_MONTHLY",
    "hyper_yearly": "STRIPE_PRICE_HYPER_YEARLY",
}

# ---------- DB Helpers ----------


@asynccontextmanager
async def get_db_pool():
    pool: Pool = await create_pool(
        DATABASE_URL,
        min_size=2,
        max_size=10,
    )
    try:
        yield pool
    finally:
        await pool.close()


async def get_user_stripe_customer_id(user_id: str) -> Optional[str]:
    """
    Lookup Stripe customer_id for a user from the DB.
    Adjust table/column names to match your schema.
    """
    async with get_db_pool() as pool:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT stripe_customer_id
                FROM public.users
                WHERE discord_id = $1;
                """,
                user_id,
            )
            return row["stripe_customer_id"] if row else None


async def get_user_subscription(user_id: str) -> dict:
    """
    Return subscription status for a user.
    First tries local DB, then Stripe if needed.
    """
    async with get_db_pool() as pool:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT subscription_status, stripe_subscription_id, stripe_plan_id
                FROM public.users
                WHERE discord_id = $1;
                """,
                user_id,
            )
            if row and row["subscription_status"]:
                return {
                    "user_id": user_id,
                    "status": row["subscription_status"],
                    "stripe_subscription_id": row["stripe_subscription_id"],
                    "stripe_plan_id": row["stripe_plan_id"],
                }

    # Fallback: no local record; could query Stripe by customer_id here if desired
    return {"user_id": user_id, "status": "none"}


# ---------- Tool Implementations ----------


async def create_checkout(price_id: str, user_id: str) -> dict:
    """
    Create a Stripe Checkout Session for a given price and user.
    Wraps logic similar to stripe_service.create_checkout_session.
    """
    if price_id not in PRICE_MAP:
        raise HTTPException(status_code=400, detail=f"Unknown price_id: {price_id}")

    price_env_name = PRICE_MAP[price_id]
    price = os.environ.get(price_env_name)
    if not price:
        raise HTTPException(status_code=500, detail=f"Price not configured: {price_env_name}")

    # Optionally lookup/create customer here; for now, we pass client_reference_id
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{"price": price, "quantity": 1}],
        mode="subscription",
        success_url=os.environ.get("STRIPE_SUCCESS_URL", "http://localhost:3000/payment-success"),
        cancel_url=os.environ.get("STRIPE_CANCEL_URL", "http://localhost:3000/pricing"),
        client_reference_id=user_id,
    )

    return {
        "success": True,
        "checkout_url": session.url,
        "session_id": session.id,
        "price_id": price_id,
        "user_id": user_id,
    }


async def handle_webhook_event(payload: str, sig_header: str) -> dict:
    """
    Verify and handle a Stripe webhook event.
    Wraps logic similar to stripe_service.handle_webhook.
    """
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        return {"success": False, "error": str(e)}

    # Here we just return the event type + id; in a fuller version, you'd
    # replicate the event handling logic from stripe_service.py (award tokens, etc.)
    return {
        "success": True,
        "event_type": event["type"],
        "event_id": event["id"],
        "note": "Event verified; full handling logic can be wired here.",
    }


async def get_subscription(user_id: str) -> dict:
    """
    Return the current subscription status for a user.
    """
    return await get_user_subscription(user_id)


# ---------- Resource Implementations ----------


async def get_subscription_resource(user_id: str) -> dict:
    """
    Resource handler for stripe://subscription/{user_id}
    """
    return await get_user_subscription(user_id)


async def get_plans_resource() -> list:
    """
    Resource handler for stripe://plans
    Returns list of available plan IDs.
    """
    return list(PRICE_MAP.keys())


# ---------- MCP Server ----------

app = FastAPI(title="Stripe MCP Server")

TOOLS = {
    "create_checkout": {
        "name": "create_checkout",
        "description": "Create a Stripe Checkout Session for a given price and user.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "price_id": {"type": "string"},
                "user_id": {"type": "string"},
            },
            "required": ["price_id", "user_id"],
        },
    },
    "handle_webhook_event": {
        "name": "handle_webhook_event",
        "description": "Verify and handle a Stripe webhook event.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "payload": {"type": "string"},
                "sig_header": {"type": "string"},
            },
            "required": ["payload", "sig_header"],
        },
    },
    "get_subscription": {
        "name": "get_subscription",
        "description": "Return the current subscription status for a user.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
            },
            "required": ["user_id"],
        },
    },
}

RESOURCES = {
    "stripe_subscription": {
        "uriTemplate": "stripe://subscription/{user_id}",
        "name": "stripe_subscription",
        "description": "Read-only resource exposing a user's subscription status.",
    },
    "stripe_plans": {
        "uriTemplate": "stripe://plans",
        "name": "stripe_plans",
        "description": "Read-only resource listing available Stripe plans.",
    },
}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/.well-known/mcp")
async def mcp_discovery():
    return {"tools": TOOLS, "resources": RESOURCES}


@app.post("/mcp/tools/{tool_name}")
async def call_tool(tool_name: str, request: Request):
    body = await request.json()

    if tool_name == "create_checkout":
        result = await create_checkout(
            price_id=body["price_id"],
            user_id=body["user_id"],
        )
    elif tool_name == "handle_webhook_event":
        result = await handle_webhook_event(
            payload=body["payload"],
            sig_header=body["sig_header"],
        )
    elif tool_name == "get_subscription":
        result = await get_subscription(user_id=body["user_id"])
    else:
        raise HTTPException(status_code=404, detail=f"Unknown tool: {tool_name}")

    return {"result": result}


@app.get("/mcp/resources/stripe://subscription/{user_id}")
async def resource_subscription(user_id: str):
    return await get_subscription_resource(user_id)


@app.get("/mcp/resources/stripe://plans")
async def resource_plans():
    return await get_plans_resource()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8100)
