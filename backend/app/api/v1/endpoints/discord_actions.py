from __future__ import annotations

import hmac
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import models
from app.models.broski import DiscordIdempotencyKey
from app.services import broski_service

router = APIRouter()


class DiscordContext(BaseModel):
    user_id: str
    guild_id: str
    channel_id: str
    interaction_id: str


class DiscordActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["daily.claim", "economy.balance"] = Field(...)
    discord: DiscordContext
    payload: dict[str, Any] = Field(default_factory=dict)


def _require_bot_auth(authorization: str = Header(...)) -> None:
    value = (authorization or "").strip()
    if not value.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authorization: Bearer required")
    token = value.split(" ", 1)[1].strip()
    expected = (settings.BOT_API_KEY or settings.API_KEY or "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="BOT_API_KEY not configured")
    if not token or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=403, detail="Invalid bot API key")


def _resolve_user_by_discord_id(discord_id: str, db: Session) -> models.User:
    user = db.query(models.User).filter(models.User.discord_id == discord_id).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="No V2.4 account linked to that Discord ID",
        )
    return user


def _wallet_snapshot(discord_id: str, db: Session) -> dict[str, Any]:
    user = _resolve_user_by_discord_id(discord_id, db)
    wallet = broski_service.get_wallet(user.id, db)

    now = datetime.now(timezone.utc)
    last = wallet.last_daily_login
    if last is not None and last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    daily_claimed = bool(last and (now - last) < timedelta(hours=24))

    return {
        "discord_id": discord_id,
        "coins": wallet.coins,
        "xp": wallet.xp,
        "level": wallet.level,
        "level_name": wallet.level_name,
        "daily_claimed": daily_claimed,
    }


def _render_wallet_embed(*, title: str, snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "embed",
        "title": title,
        "description": "",
        "color": "#5865F2",
        "fields": [
            {"name": "Coins", "value": str(snapshot["coins"]), "inline": True},
            {"name": "XP", "value": str(snapshot["xp"]), "inline": True},
            {"name": "Level", "value": str(snapshot["level"]), "inline": True},
        ],
        "footer": "BROski Bot • HyperCode Core",
    }


def _idempotency_lookup(
    *,
    idempotency_key: str,
    request_hash: str,
    db: Session,
) -> tuple[Optional[dict[str, Any]], bool]:
    existing = (
        db.query(DiscordIdempotencyKey)
        .filter(DiscordIdempotencyKey.idempotency_key == idempotency_key)
        .first()
    )
    if not existing:
        return None, False
    if existing.request_hash != request_hash:
        return {
            "status": "error",
            "code": "idempotency_mismatch",
            "message": "Idempotency-Key reused with different request",
            "retryable": False,
        }, True
    try:
        return json.loads(existing.response_json), False
    except Exception:
        return None, False


def _idempotency_store(
    *,
    idempotency_key: str,
    request_hash: str,
    action: str,
    response: dict[str, Any],
    db: Session,
) -> None:
    row = DiscordIdempotencyKey(
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        action=action,
        response_json=json.dumps(response),
    )
    db.add(row)
    db.commit()


def _compute_request_hash(req: DiscordActionRequest) -> str:
    body = req.model_dump()
    raw = json.dumps(body, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()[:16]


@router.post("/actions")
def discord_actions(
    req: DiscordActionRequest,
    db: Session = Depends(get_db),
    _: None = Depends(_require_bot_auth),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    request_hash_header: str = Header(..., alias="X-Request-Hash"),
) -> Any:
    request_hash = _compute_request_hash(req)
    if request_hash_header != request_hash:
        return JSONResponse(
            status_code=422,
            content={
                "status": "error",
                "code": "request_hash_mismatch",
                "message": "X-Request-Hash does not match request body",
                "retryable": False,
            },
        )

    cached, mismatch = _idempotency_lookup(
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        db=db,
    )
    if mismatch:
        return JSONResponse(status_code=409, content=cached)
    if cached is not None:
        return JSONResponse(status_code=409, content=cached)

    discord_id = req.discord.user_id

    if req.action == "daily.claim":
        user = _resolve_user_by_discord_id(discord_id, db)
        wallet, awarded = broski_service.handle_daily_login(user.id, db)
        snapshot = _wallet_snapshot(discord_id, db)
        title = "Daily claimed" if awarded else "Daily already claimed"
        render = _render_wallet_embed(title=title, snapshot=snapshot)
        response: dict[str, Any] = {
            "status": "ok",
            "action": req.action,
            "data": snapshot,
            "render": render,
        }
        _idempotency_store(
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            action=req.action,
            response=response,
            db=db,
        )
        return response

    if req.action == "economy.balance":
        snapshot = _wallet_snapshot(discord_id, db)
        render = _render_wallet_embed(title="Balance", snapshot=snapshot)
        response = {
            "status": "ok",
            "action": req.action,
            "data": snapshot,
            "render": render,
        }
        _idempotency_store(
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            action=req.action,
            response=response,
            db=db,
        )
        return response

    raise HTTPException(status_code=422, detail="Unsupported action")
