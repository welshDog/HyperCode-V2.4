"""
Access — Phase 3 Agent Access + Shop Bridge

POST /api/v1/access/provision
  Called by the Supabase provision-access edge function when a student
  buys "Agent Sandbox Access" (300 tokens) in the Course shop.

  1. Validates X-Sync-Secret header.
  2. Deduplicates on source_id (shop_purchases.id) — 409 if already done.
  3. Looks up the V2.4 user by discord_id (404 if not linked yet).
  4. Generates a unique hc_ API key.
  5. Stores an access_provisions record.
  6. Sends a Discord DM to the student via the Discord HTTP API.
  7. Returns { api_key, mission_control_url }.

GET /api/v1/access/my-provisions
  Authenticated — returns the current user's active provisions.
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import models
from app.api import deps

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Schemas ───────────────────────────────────────────────────────────────────


class ProvisionRequest(BaseModel):
    source_id: str = Field(..., max_length=128, description="shop_purchases.id — idempotency key")
    discord_id: str = Field(..., max_length=32)
    item_slug: str = Field(..., max_length=64, description="Must be 'agent-sandbox-access'")


class ProvisionResponse(BaseModel):
    provisioned: bool
    api_key: str
    mission_control_url: str
    discord_dm_sent: bool
    source_id: str


class ProvisionRecord(BaseModel):
    id: int
    provision_type: str
    api_key: str
    mission_control_url: Optional[str]
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


# ── Helpers ───────────────────────────────────────────────────────────────────

ALLOWED_ITEMS = {"agent-sandbox-access"}


def _verify_shop_secret(x_sync_secret: str = Header(..., alias="X-Sync-Secret")) -> None:
    expected = settings.SHOP_SYNC_SECRET
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="SHOP_SYNC_SECRET not configured — shop bridge disabled",
        )
    if x_sync_secret != expected:
        raise HTTPException(status_code=401, detail="Invalid sync secret")


def _generate_api_key() -> str:
    return f"hc_{secrets.token_urlsafe(32)}"


async def _send_discord_dm(discord_id: str, api_key: str, mission_control_url: str) -> bool:
    """Send a DM to the student via Discord HTTP API. Returns True on success."""
    bot_token = settings.DISCORD_BOT_TOKEN
    if not bot_token:
        logger.warning("DISCORD_BOT_TOKEN not set — skipping DM")
        return False

    message = (
        "🦅 **HyperCode Sandbox Access — Provisioned!**\n\n"
        "You bought **Agent Sandbox Access** in the Hyper-Vibe Coding Course.\n"
        "Here are your credentials:\n\n"
        f"🔑 **API Key:** `{api_key}`\n"
        f"🖥️ **Mission Control:** {mission_control_url}\n\n"
        "Keep your API key secret. Paste it into Mission Control to log in.\n"
        "Welcome to the stack, BROski! 🔥"
    )

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            # Step 1 — open DM channel
            dm_res = await client.post(
                "https://discord.com/api/v10/users/@me/channels",
                headers={
                    "Authorization": f"Bot {bot_token}",
                    "Content-Type": "application/json",
                },
                json={"recipient_id": discord_id},
            )
            if dm_res.status_code not in (200, 201):
                logger.warning("Failed to open DM channel for %s: %s", discord_id, dm_res.text)
                return False

            channel_id = dm_res.json()["id"]

            # Step 2 — send message
            msg_res = await client.post(
                f"https://discord.com/api/v10/channels/{channel_id}/messages",
                headers={
                    "Authorization": f"Bot {bot_token}",
                    "Content-Type": "application/json",
                },
                json={"content": message},
            )
            if msg_res.status_code not in (200, 201):
                logger.warning("Failed to send DM to %s: %s", discord_id, msg_res.text)
                return False

    except Exception as exc:
        logger.warning("Discord DM error for %s: %s", discord_id, exc)
        return False

    logger.info("✅ Discord DM sent to %s", discord_id)
    return True


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.post(
    "/provision",
    response_model=ProvisionResponse,
    status_code=200,
    summary="Provision sandbox access from a Course shop purchase (idempotent)",
)
async def provision_access(
    payload: ProvisionRequest,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_shop_secret),
) -> Any:
    """
    Called by the Supabase `provision-access` edge function on shop_purchases INSERT.
    Idempotent on source_id — returns 409 if already provisioned.
    """
    # ── 1. Item guard ──────────────────────────────────────────────────────
    if payload.item_slug not in ALLOWED_ITEMS:
        raise HTTPException(
            status_code=422,
            detail=f"item_slug '{payload.item_slug}' is not a provisionable item",
        )

    # ── 2. Idempotency check ───────────────────────────────────────────────
    existing = (
        db.query(models.AccessProvision)
        .filter(models.AccessProvision.source_id == payload.source_id)
        .first()
    )
    if existing:
        logger.info("Provision duplicate ignored: source_id=%s", payload.source_id)
        raise HTTPException(
            status_code=409,
            detail=f"source_id '{payload.source_id}' already provisioned",
        )

    # ── 3. Resolve discord_id → V2.4 user ─────────────────────────────────
    user = (
        db.query(models.User)
        .filter(models.User.discord_id == payload.discord_id)
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No V2.4 account linked to Discord {payload.discord_id}. "
                "Student must link via /link-discord first."
            ),
        )

    # ── 4. Generate key + store provision ─────────────────────────────────
    api_key = _generate_api_key()
    mission_url = settings.MISSION_CONTROL_URL

    provision = models.AccessProvision(
        user_id=user.id,
        discord_id=payload.discord_id,
        api_key=api_key,
        provision_type="agent_sandbox",
        source_id=payload.source_id,
        mission_control_url=mission_url,
        is_active=True,
    )
    db.add(provision)
    try:
        db.commit()
        db.refresh(provision)
    except IntegrityError:
        db.rollback()
        logger.warning("Provision race condition for source_id=%s", payload.source_id)
        raise HTTPException(
            status_code=409,
            detail=f"source_id '{payload.source_id}' already provisioned (race)",
        )

    logger.info(
        "✅ Sandbox provisioned: user=%s discord=%s source_id=%s",
        user.id, payload.discord_id, payload.source_id,
    )

    # ── 5. Discord DM ──────────────────────────────────────────────────────
    dm_sent = await _send_discord_dm(payload.discord_id, api_key, mission_url)

    return ProvisionResponse(
        provisioned=True,
        api_key=api_key,
        mission_control_url=mission_url,
        discord_dm_sent=dm_sent,
        source_id=payload.source_id,
    )


@router.get(
    "/my-provisions",
    response_model=list[ProvisionRecord],
    summary="List your active sandbox provisions",
)
def my_provisions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """Returns all active access provisions for the logged-in user."""
    return (
        db.query(models.AccessProvision)
        .filter(
            models.AccessProvision.user_id == current_user.id,
            models.AccessProvision.is_active.is_(True),
        )
        .order_by(models.AccessProvision.created_at.desc())
        .all()
    )
