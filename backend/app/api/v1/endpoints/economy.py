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
import secrets
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
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


class SupabaseDbWebhookPayload(BaseModel):
    model_config = ConfigDict(extra="allow")
    type: Literal["INSERT", "UPDATE", "DELETE"]
    table: str
    record: dict[str, Any] | None = None
    old_record: dict[str, Any] | None = None


# ── Helpers ────────────────────────────────────────────────────────────────


def _verify_sync_secret(x_sync_secret: str = Header(..., alias="X-Sync-Secret")) -> None:
    """Reject requests that don't carry the shared secret."""
    expected = settings.COURSE_SYNC_SECRET
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="COURSE_SYNC_SECRET not configured — token sync disabled",
        )
    if not secrets.compare_digest(x_sync_secret, expected):
        raise HTTPException(status_code=401, detail="Invalid sync secret")


def _award_from_course(payload: CourseAwardRequest, db: Session) -> CourseAwardResponse:
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
        db.rollback()
        logger.warning("Token sync race condition caught for source_id=%s", payload.source_id)
        raise HTTPException(
            status_code=409,
            detail=f"source_id '{payload.source_id}' already processed (race) — no double award",
        )

    logger.info(
        "✅ Token sync: +%d coins to user %s (discord=%s, source_id=%s)",
        payload.tokens,
        user.id,
        payload.discord_id,
        payload.source_id,
    )

    return CourseAwardResponse(
        awarded=True,
        coins_balance=wallet.coins,
        xp_balance=wallet.xp,
        level=wallet.level,
        source_id=payload.source_id,
    )


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
    return _award_from_course(payload, db)


@router.post(
    "/webhook/token-transactions",
    response_model=CourseAwardResponse,
    status_code=200,
    summary="Supabase Database Webhook → award BROski$ (INSERT token_transactions)",
)
def supabase_webhook_token_transactions(
    body: SupabaseDbWebhookPayload,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_sync_secret),
) -> CourseAwardResponse:
    if body.type != "INSERT":
        raise HTTPException(status_code=422, detail="Only INSERT webhooks are supported")
    if body.table != "token_transactions":
        raise HTTPException(status_code=422, detail="Unsupported table for this webhook")
    if not body.record:
        raise HTTPException(status_code=422, detail="Missing record")

    record = body.record
    source_id = str(record.get("id") or record.get("source_id") or record.get("sourceId") or "").strip()
    discord_id = str(record.get("discord_id") or record.get("discordId") or "").strip()
    tokens_raw = record.get("tokens")
    if tokens_raw is None:
        tokens_raw = record.get("amount")
    try:
        tokens = int(tokens_raw)
    except Exception:
        tokens = 0
    reason = str(record.get("reason") or "Course reward").strip()

    if not source_id:
        raise HTTPException(status_code=422, detail="record.id is required")
    if not discord_id:
        raise HTTPException(status_code=422, detail="record.discord_id is required")
    if tokens <= 0:
        raise HTTPException(status_code=422, detail="record.tokens must be a positive integer")

    return _award_from_course(
        CourseAwardRequest(source_id=source_id, discord_id=discord_id, tokens=tokens, reason=reason),
        db,
    )


# ── Dev-action XP → durable BROski$ wallet ──────────────────────────────────
# Durable sink for the broski_economy consumer. Hook XP awards (14 repos) were
# only persisted in volatile redis; this routes them through the canonical
# broski_service.award_xp so they land in broski_wallets / broski_transactions
# (system of record) and survive restarts for real. See
# scripts/broski_economy_consumer.py.


class DevXpAwardRequest(BaseModel):
    discord_id: str = Field(..., max_length=32, description="Owner of the dev-action XP stream")
    xp: int = Field(..., gt=0, le=100_000)
    reason: str = Field(default="dev action", max_length=255)
    source: str = Field(default="unknown", max_length=128, description="Repo/hook that emitted the award")
    full_name: str = Field(default="HyperFocus Dev", max_length=255)


class DevXpAwardResponse(BaseModel):
    awarded: bool
    user_id: int
    xp_balance: int
    level: int
    level_name: str
    level_up: Optional[str] = None


def _verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> None:
    """Gate the internal dev-xp sink with the master API_KEY (service-to-service)."""
    expected = settings.API_KEY
    if not expected:
        raise HTTPException(status_code=503, detail="API_KEY not configured — dev-xp award disabled")
    if not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid API key")


def _get_or_create_user_by_discord(discord_id: str, full_name: str, db: Session) -> models.User:
    user = (
        db.query(models.User)
        .filter(models.User.discord_id == discord_id)
        .first()
    )
    if user:
        return user
    # System/dev identity — never password-logs-in, so the hash is intentionally unusable.
    user = models.User(
        email=f"{discord_id}@dev.hyperfocus.zone",
        hashed_password="!",
        full_name=full_name,
        discord_id=discord_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("🆕 dev-economy user provisioned for discord_id=%s (user %s)", discord_id, user.id)
    return user


@router.post(
    "/award-dev-xp",
    response_model=DevXpAwardResponse,
    status_code=200,
    summary="Award dev-action XP into the durable BROski$ wallet (internal, API-key gated)",
)
def award_dev_xp(
    payload: DevXpAwardRequest,
    db: Session = Depends(get_db),
    _: None = Depends(_verify_api_key),
) -> Any:
    user = _get_or_create_user_by_discord(payload.discord_id, payload.full_name, db)
    wallet, level_up = broski_service.award_xp(
        user_id=user.id,
        amount=payload.xp,
        reason=payload.reason,
        db=db,
        meta={"source": payload.source, "stream": "dev-action"},
    )
    logger.info(
        "⚡ dev-xp: +%d xp to user %s (discord=%s, source=%s, reason=%s)",
        payload.xp, user.id, payload.discord_id, payload.source, payload.reason,
    )
    return DevXpAwardResponse(
        awarded=True,
        user_id=user.id,
        xp_balance=wallet.xp,
        level=wallet.level,
        level_name=wallet.level_name,
        level_up=level_up,
    )
