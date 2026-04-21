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

import hmac
import logging
import secrets
import uuid
from datetime import datetime
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
    purchase_id: str = Field(..., description="uuid-from-shop_purchases.id")
    user_id: str = Field(..., description="Course user UUID")
    discord_id: Optional[str] = Field(default=None, max_length=32)
    item_type: str = Field(..., max_length=32)
    v24_tier: str = Field(..., max_length=32)
    idempotency_key: str = Field(..., max_length=128, description="shop_purchase:<purchase_id>")


class ProvisionResponse(BaseModel):
    status: str
    api_key: str
    mission_control_url: str
    expires_at: Optional[str]
    provision_event_id: str


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


def _verify_shop_secret(x_sync_secret: str = Header(..., alias="X-Sync-Secret")) -> None:
    expected = settings.SHOP_SYNC_SECRET
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="SHOP_SYNC_SECRET not configured — shop bridge disabled",
        )
    if not hmac.compare_digest(x_sync_secret, expected):
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
    if payload.item_type != "agent_access":
        raise HTTPException(
            status_code=422,
            detail=f"item_type '{payload.item_type}' is not provisionable",
        )

    if not payload.discord_id:
        raise HTTPException(status_code=422, detail="discord_id is required for provisioning")

    existing = (
        db.query(models.AccessProvision)
        .filter(models.AccessProvision.source_id == payload.idempotency_key)
        .first()
    )
    if existing:
        logger.info("Provision duplicate ignored: idempotency_key=%s", payload.idempotency_key)
        raise HTTPException(
            status_code=409,
            detail=f"idempotency_key '{payload.idempotency_key}' already provisioned",
        )

    user = db.query(models.User).filter(models.User.discord_id == payload.discord_id).first()
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
    provision_event_id = str(uuid.uuid4())

    provision = models.AccessProvision(
        user_id=user.id,
        discord_id=payload.discord_id,
        api_key=api_key,
        provision_type=f"agent_access:{payload.v24_tier}",
        source_id=payload.idempotency_key,
        mission_control_url=mission_url,
        is_active=True,
        event_id=provision_event_id,
    )
    db.add(provision)
    try:
        db.commit()
        db.refresh(provision)
    except IntegrityError:
        db.rollback()
        logger.warning("Provision race condition for idempotency_key=%s", payload.idempotency_key)
        raise HTTPException(
            status_code=409,
            detail=f"idempotency_key '{payload.idempotency_key}' already provisioned (race)",
        )

    logger.info(
        "✅ Agent access provisioned: user=%s discord=%s idempotency_key=%s",
        user.id, payload.discord_id, payload.idempotency_key,
    )

    # ── 5. Discord DM ──────────────────────────────────────────────────────
    await _send_discord_dm(payload.discord_id, api_key, mission_url)

    return ProvisionResponse(
        status="provisioned",
        api_key=api_key,
        mission_control_url=mission_url,
        expires_at=provision.expires_at.isoformat() if provision.expires_at else None,
        provision_event_id=provision_event_id,
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
