import secrets
import httpx
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.session import get_db
from app.models.graduate import GraduationEvent
from app.models.models import User
from app.core.config import settings

router = APIRouter()


class GraduateRequest(BaseModel):
    discord_id: str
    source_id: str  # unique id from course graduation_events table
    badge_slug: Optional[str] = 'hyper-graduate'
    tokens_awarded: Optional[int] = 500
    portfolio_url: Optional[str] = None


class GraduateResponse(BaseModel):
    status: str
    discord_id: str
    badge_slug: str
    tokens_awarded: int
    portfolio_url: Optional[str]
    discord_role_assigned: bool
    message: str


async def _send_discord_dm(discord_id: str, badge_slug: str, tokens: int, portfolio_url: Optional[str]):
    """Send graduation DM via Discord HTTP API."""
    bot_token = settings.DISCORD_BOT_TOKEN
    if not bot_token:
        return False

    portfolio_line = f"\n\ud83c\udf10 **Portfolio:** {portfolio_url}" if portfolio_url else ""
    message = (
        f"\ud83c\udf93 **CONGRATULATIONS, GRADUATE!** \ud83d\udd25\n\n"
        f"You just completed the Hyper Vibe Coding Course!\n"
        f"\ud83c\udfc5 Badge unlocked: `{badge_slug}`\n"
        f"\ud83d\udcb0 BROski$ bonus: **+{tokens} tokens** incoming!\n"
        f"{portfolio_line}\n"
        f"Welcome to the Hyper Graduate squad! \u267e"
    )

    async with httpx.AsyncClient() as client:
        # Open DM channel
        dm_resp = await client.post(
            "https://discord.com/api/v10/users/@me/channels",
            headers={"Authorization": f"Bot {bot_token}", "Content-Type": "application/json"},
            json={"recipient_id": discord_id},
        )
        if dm_resp.status_code != 200:
            return False

        channel_id = dm_resp.json()["id"]

        # Send message
        msg_resp = await client.post(
            f"https://discord.com/api/v10/channels/{channel_id}/messages",
            headers={"Authorization": f"Bot {bot_token}", "Content-Type": "application/json"},
            json={"content": message},
        )
        return msg_resp.status_code == 200


@router.post("/graduate/trigger", response_model=GraduateResponse)
async def trigger_graduation(
    payload: GraduateRequest,
    x_sync_secret: str = Header(..., alias="X-Sync-Secret"),
    db: Session = Depends(get_db),
):
    """POST /api/v1/graduate/trigger
    Called by Course Supabase edge function when student completes all modules.
    Idempotent via source_id.
    """
    # Auth check
    if x_sync_secret != settings.SHOP_SYNC_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")

    # Idempotency check
    existing = db.query(GraduationEvent).filter(
        GraduationEvent.source_id == payload.source_id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Already graduated with this source_id")

    # Lookup user by discord_id
    user = db.query(User).filter(User.discord_id == payload.discord_id).first()
    user_id = user.id if user else None

    # Award BROski$ tokens via economy endpoint (internal call pattern)
    # Tokens are awarded by inserting a course_sync_event — reuse existing economy logic
    # (or call directly if user exists)
    if user:
        user.broski_tokens = (user.broski_tokens or 0) + payload.tokens_awarded
        db.add(user)

    # Send Discord DM
    dm_sent = await _send_discord_dm(
        payload.discord_id,
        payload.badge_slug,
        payload.tokens_awarded,
        payload.portfolio_url,
    )

    # Record graduation event
    event = GraduationEvent(
        user_id=user_id,
        discord_id=payload.discord_id,
        source_id=payload.source_id,
        badge_slug=payload.badge_slug,
        tokens_awarded=payload.tokens_awarded,
        portfolio_url=payload.portfolio_url,
        discord_role_assigned=dm_sent,
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    return GraduateResponse(
        status="graduated",
        discord_id=payload.discord_id,
        badge_slug=payload.badge_slug,
        tokens_awarded=payload.tokens_awarded,
        portfolio_url=payload.portfolio_url,
        discord_role_assigned=dm_sent,
        message="Graduation complete! DM sent. BROski$ awarded. \ud83d�",
    )
