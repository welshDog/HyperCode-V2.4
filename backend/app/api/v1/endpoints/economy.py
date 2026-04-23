"""
Economy — Phase 2 Token Sync endpoint

POST /api/v1/economy/award-from-course
  Called by the Supabase sync-tokens-to-v24 edge function.
  Authenticates via X-Sync-Secret header.
  Looks up the V2.4 user by discord_id, awards BROski$ coins,
  and records a CourseSyncEvent for idempotency (same source_id → 409).
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import models
from app.models.broski import CourseSyncEvent
from app.services import broski_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Request / Response schemas ─────────────────────────────────────────────


class CourseAwardRequest(BaseModel):
    source_id: str = Field(
        ...,
        description="Idempotency key — use token_transactions.id from Supabase",
        max_length=128,
    )
    discord_id: str = Field(..., max_length=32)
    tokens: int = Field(..., gt=0, le=10_000)
    reason: str = Field(default="Course reward", max_length=255)


class CourseAwardResponse(BaseModel):
    awarded: bool
    coins_balance: int
    xp_balance: int
    level: int
    source_id: str


# ── Helpers ────────────────────────────────────────────────────────────────


def _verify_sync_secret(x_sync_secret: str = Header(..., alias="X-Sync-Secret")) -> None:
    """Reject requests that don't carry the shared secret."""
    expected = settings.COURSE_SYNC_SECRET
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="COURSE_SYNC_SECRET not configured — token sync disabled",
        )
    if x_sync_secret != expected:
        raise HTTPException(status_code=401, detail="Invalid sync secret")


# ── Endpoint ────────────────────────────────────────────────────────────────


@router.post(
    "/award-from-course",
    response_model=CourseAwardResponse,
    status_code=200,
    summary="Award BROski$ from Course token transaction (idempotent)",
)
def award_from_course(
    payload: CourseAwardRequest,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_sync_secret),
) -> Any:
    """
    Called by the Supabase `sync-tokens-to-v24` edge function whenever
    a `token_transactions` row is inserted in the Course database.

    Idempotency:
      - If source_id already exists in course_sync_events → 409 (safe re-delivery)
      - DB UNIQUE constraint is the last guard if the app check races
    """
    # ── 1. Idempotency check ───────────────────────────────────────────────
    existing = (
        db.query(CourseSyncEvent)
        .filter(CourseSyncEvent.source_id == payload.source_id)
        .first()
    )
    if existing:
        logger.info("Token sync duplicate ignored: source_id=%s", payload.source_id)
        raise HTTPException(
            status_code=409,
            detail=f"source_id '{payload.source_id}' already processed — no double award",
        )

    # ── 2. Resolve discord_id → V2.4 user ─────────────────────────────────
    user = (
        db.query(models.User)
        .filter(models.User.discord_id == payload.discord_id)
        .first()
    )
    if not user:
        # Not linked yet — record the event as unmatched so it can be retried
        # once the user links their Discord account.
        logger.warning(
            "Token sync: no V2.4 user for discord_id=%s (source_id=%s) — skipping award",
            payload.discord_id,
            payload.source_id,
        )
        raise HTTPException(
            status_code=404,
            detail=(
                f"No V2.4 account linked to Discord {payload.discord_id}. "
                "Ask the user to link via /link-discord."
            ),
        )

    # ── 3. Award coins ─────────────────────────────────────────────────────
    wallet = broski_service.award_coins(
        user_id=user.id,
        amount=payload.tokens,
        reason=f"Course sync: {payload.reason}",
        db=db,
        meta={"source": "course", "source_id": payload.source_id, "discord_id": payload.discord_id},
    )

    # ── 4. Log the sync event (dedup record) ───────────────────────────────
    sync_event = CourseSyncEvent(
        source_id=payload.source_id,
        discord_id=payload.discord_id,
        tokens_awarded=payload.tokens,
        reason=payload.reason,
    )
    db.add(sync_event)
    try:
        db.commit()
    except IntegrityError:
        # Race condition: another request committed the same source_id first
        db.rollback()
        logger.warning("Token sync race condition caught for source_id=%s", payload.source_id)
        raise HTTPException(
            status_code=409,
            detail=f"source_id '{payload.source_id}' already processed (race) — no double award",
        )

    logger.info(
        "✅ Token sync: +%d coins to user %s (discord=%s, source_id=%s)",
        payload.tokens, user.id, payload.discord_id, payload.source_id,
    )

    return CourseAwardResponse(
        awarded=True,
        coins_balance=wallet.coins,
        xp_balance=wallet.xp,
        level=wallet.level,
        source_id=payload.source_id,
    )
