from __future__ import annotations

import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import models
from app.models.broski import BROskiWallet, DiscordIdempotencyKey
from app.services import broski_service

router = APIRouter()

_RANK_MEDALS = ["🥇", "🥈", "🥉"]


class DiscordContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    user_id: str
    username: Optional[str] = None
    guild_id: Optional[str] = None
    channel_id: Optional[str] = None
    interaction_id: str


class DiscordActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal[
        "ai.ask",
        "ai.chat",
        "daily.claim",
        "economy.balance",
        "economy.give",
        "economy.leaderboard",
        "leaderboard.xp",
        "member.join",
    ] = Field(...)
    discord: DiscordContext
    payload: dict[str, Any] = Field(default_factory=dict)


def _require_bot_auth(authorization: Optional[str] = Header(default=None)) -> None:
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
            {"name": "💰 Coins", "value": f"{snapshot['coins']:,}", "inline": True},
            {"name": "⚡ XP", "value": f"{snapshot['xp']:,}", "inline": True},
            {"name": "🎮 Level", "value": f"{snapshot['level']} — {snapshot['level_name']}", "inline": True},
        ],
        "footer": "BROski Bot • HyperCode Core",
    }


def _render_info_embed(*, title: str, description: str, color: str = "#5865F2") -> dict[str, Any]:
    return {
        "type": "embed",
        "title": title,
        "description": description,
        "color": color,
        "fields": [],
        "footer": "BROski Bot • HyperCode Core",
    }


def _truncate(text: str, limit: int = 3500) -> str:
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + "…"


def _extract_orchestrator_text(payload: dict[str, Any]) -> str:
    result = payload.get("result")
    if isinstance(result, str) and result.strip():
        return result.strip()
    if isinstance(result, dict):
        for k in ("message", "analysis", "answer", "reply"):
            v = result.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        return json.dumps(result, ensure_ascii=False)[:3500]
    msg = payload.get("message")
    if isinstance(msg, str) and msg.strip():
        return msg.strip()
    return json.dumps(payload, ensure_ascii=False)[:3500]


def _rank_prefix(i: int) -> str:
    """Return medal emoji for top 3, number for the rest."""
    if i <= len(_RANK_MEDALS):
        return _RANK_MEDALS[i - 1]
    return f"#{i}"


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


@router.post("/actions")
def discord_actions(
    req: DiscordActionRequest,
    db: Session = Depends(get_db),
    _: None = Depends(_require_bot_auth),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    request_hash_header: str = Header(..., alias="X-Request-Hash"),
) -> Any:
    request_hash = request_hash_header

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

    # ── member.join ──────────────────────────────────────────────────────────
    if req.action == "member.join":
        response: dict[str, Any] = {
            "status": "ok",
            "action": req.action,
            "data": {"discord_id": discord_id},
            "render": _render_info_embed(
                title="⚡ Welcome to HyperFocus Zone!",
                description=(
                    "Use `/daily` to grab your daily BROski$ coins.\n"
                    "Use `/balance` to check your wallet.\n"
                    "Link your HyperCode account to unlock full rewards."
                ),
            ),
        }
        _idempotency_store(
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            action=req.action,
            response=response,
            db=db,
        )
        return response

    # ── ai.ask / ai.chat ─────────────────────────────────────────────────────
    if req.action in {"ai.ask", "ai.chat"}:
        key = "question" if req.action == "ai.ask" else "message"
        prompt = str(req.payload.get(key) or "").strip()

        if not prompt:
            response = {
                "status": "ok",
                "action": req.action,
                "data": {"ok": False},
                "render": _render_info_embed(
                    title="❌ Missing text",
                    description=f"Send `{key}` in payload.",
                    color="#ED4245",
                ),
            }
        elif not settings.ORCHESTRATOR_URL:
            response = {
                "status": "ok",
                "action": req.action,
                "data": {"ok": False},
                "render": _render_info_embed(
                    title="🛑 Orchestrator offline",
                    description="ORCHESTRATOR_URL is not configured in Core.",
                    color="#ED4245",
                ),
            }
        elif not settings.ORCHESTRATOR_API_KEY:
            response = {
                "status": "ok",
                "action": req.action,
                "data": {"ok": False},
                "render": _render_info_embed(
                    title="🛑 Orchestrator auth missing",
                    description="ORCHESTRATOR_API_KEY is not configured in Core.",
                    color="#ED4245",
                ),
            }
        else:
            orch_url = str(settings.ORCHESTRATOR_URL).rstrip("/")
            body = {
                "id": f"discord-{req.discord.interaction_id}",
                "task": prompt,
                "type": "discord_ai",
                "agent": "coder-agent",
                "requires_approval": False,
                "context": {
                    "discord_id": discord_id,
                    "username": req.discord.username,
                    "mode": req.action,
                },
            }
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(
                        f"{orch_url}/task",
                        json=body,
                        headers={"X-API-Key": settings.ORCHESTRATOR_API_KEY},
                    )
                if resp.status_code != 200:
                    raise RuntimeError(
                        f"orchestrator_http_{resp.status_code}"
                    )
                orch_payload = resp.json()
                text = _truncate(_extract_orchestrator_text(orch_payload))
                title = "🧠 BROski" if req.action == "ai.chat" else "❓ Answer"
                response = {
                    "status": "ok",
                    "action": req.action,
                    "data": {"ok": True},
                    "render": _render_info_embed(
                        title=title,
                        description=text,
                        color="#3498DB",
                    ),
                }
            except Exception:
                response = {
                    "status": "ok",
                    "action": req.action,
                    "data": {"ok": False},
                    "render": _render_info_embed(
                        title="⚠️ AI unavailable",
                        description="Crew is offline or still booting. Try again.",
                        color="#FEE75C",
                    ),
                }

        _idempotency_store(
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            action=req.action,
            response=response,
            db=db,
        )
        return response

    # ── daily.claim ──────────────────────────────────────────────────────────
    if req.action == "daily.claim":
        user = db.query(models.User).filter(models.User.discord_id == discord_id).first()
        if not user:
            response = {
                "status": "ok",
                "action": req.action,
                "data": {"linked": False, "discord_id": discord_id},
                "render": _render_info_embed(
                    title="🔗 Link required",
                    description="No HyperCode account is linked to this Discord ID yet.",
                    color="#ED4245",
                ),
            }
        else:
            _, awarded = broski_service.handle_daily_login(user.id, db)
            snapshot = _wallet_snapshot(discord_id, db)
            title = "✅ Daily claimed!" if awarded else "⏳ Daily already claimed"
            response = {
                "status": "ok",
                "action": req.action,
                "data": snapshot,
                "render": _render_wallet_embed(title=title, snapshot=snapshot),
            }
        _idempotency_store(
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            action=req.action,
            response=response,
            db=db,
        )
        return response

    # ── economy.balance ───────────────────────────────────────────────────────
    if req.action == "economy.balance":
        user = db.query(models.User).filter(models.User.discord_id == discord_id).first()
        if not user:
            response = {
                "status": "ok",
                "action": req.action,
                "data": {"linked": False, "discord_id": discord_id},
                "render": _render_info_embed(
                    title="🔗 Link required",
                    description="No HyperCode account is linked to this Discord ID yet.",
                    color="#ED4245",
                ),
            }
        else:
            snapshot = _wallet_snapshot(discord_id, db)
            response = {
                "status": "ok",
                "action": req.action,
                "data": snapshot,
                "render": _render_wallet_embed(title="💰 Your BROski$ Wallet", snapshot=snapshot),
            }
        _idempotency_store(
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            action=req.action,
            response=response,
            db=db,
        )
        return response

    # ── economy.give ──────────────────────────────────────────────────────────
    if req.action == "economy.give":
        to_discord_id = str(req.payload.get("to_discord_id") or "").strip()
        to_username = str(req.payload.get("to_username") or "").strip()
        try:
            amount = int(req.payload.get("amount"))
        except Exception:
            amount = 0

        if not to_discord_id or amount <= 0:
            response = {
                "status": "ok",
                "action": req.action,
                "data": {"ok": False},
                "render": _render_info_embed(
                    title="❌ Invalid request",
                    description="Amount must be a positive integer and a recipient must be provided.",
                    color="#ED4245",
                ),
            }
        elif to_discord_id == discord_id:
            response = {
                "status": "ok",
                "action": req.action,
                "data": {"ok": False},
                "render": _render_info_embed(
                    title="🤔 Nice try!",
                    description="You can't give coins to yourself, BRO.",
                    color="#FEE75C",
                ),
            }
        else:
            sender = db.query(models.User).filter(models.User.discord_id == discord_id).first()
            recipient = db.query(models.User).filter(models.User.discord_id == to_discord_id).first()
            if not sender or not recipient:
                missing = []
                if not sender:
                    missing.append(f"<@{discord_id}> (sender)")
                if not recipient:
                    missing.append(f"<@{to_discord_id}> (recipient)")
                response = {
                    "status": "ok",
                    "action": req.action,
                    "data": {"ok": False},
                    "render": _render_info_embed(
                        title="🔗 Link required",
                        description=f"These members need to link their HyperCode accounts: {', '.join(missing)}",
                        color="#ED4245",
                    ),
                }
            else:
                try:
                    broski_service.spend_coins(
                        user_id=sender.id,
                        amount=amount,
                        reason=f"Gift to Discord {to_discord_id}",
                        db=db,
                        meta={"from": discord_id, "to": to_discord_id},
                    )
                    broski_service.award_coins(
                        user_id=recipient.id,
                        amount=amount,
                        reason=f"Gift from Discord {discord_id}",
                        db=db,
                        meta={"from": discord_id, "to": to_discord_id},
                    )
                    sender_snapshot = _wallet_snapshot(discord_id, db)
                    recipient_label = f"<@{to_discord_id}>" if not to_username else f"{to_username} (<@{to_discord_id}>)"
                    response = {
                        "status": "ok",
                        "action": req.action,
                        "data": {"ok": True, "from": sender_snapshot},
                        "render": {
                            "type": "embed",
                            "title": f"🎁 Sent {amount:,} BROski$ to {recipient_label}!",
                            "description": "Generosity is the BROski way. 🐶♾️",
                            "color": "#57F287",
                            "fields": [
                                {
                                    "name": "💰 Your remaining balance",
                                    "value": f"{sender_snapshot['coins']:,} coins",
                                    "inline": True,
                                },
                                {
                                    "name": "⚡ Your XP",
                                    "value": f"{sender_snapshot['xp']:,}",
                                    "inline": True,
                                },
                                {
                                    "name": "🎮 Level",
                                    "value": f"{sender_snapshot['level']} — {sender_snapshot['level_name']}",
                                    "inline": True,
                                },
                            ],
                            "footer": "BROski Bot • HyperCode Core",
                        },
                    }
                except ValueError as exc:
                    response = {
                        "status": "ok",
                        "action": req.action,
                        "data": {"ok": False},
                        "render": _render_info_embed(
                            title="💸 Not enough coins!",
                            description=str(exc),
                            color="#ED4245",
                        ),
                    }

        _idempotency_store(
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            action=req.action,
            response=response,
            db=db,
        )
        return response

    # ── economy.leaderboard ───────────────────────────────────────────────────
    if req.action == "economy.leaderboard":
        try:
            limit = int(req.payload.get("limit", 10))
        except Exception:
            limit = 10
        limit = max(1, min(limit, 20))

        rows = broski_service.get_leaderboard(db, limit=limit)
        fields = []
        for i, w in enumerate(rows, start=1):
            u = db.query(models.User).filter(models.User.id == w.user_id).first()
            mention = f"<@{u.discord_id}>" if u and u.discord_id else f"User {w.user_id}"
            level_tag = f"Lvl {w.level} — {w.level_name}" if hasattr(w, "level") and w.level else ""
            value_parts = [f"**{w.coins:,}** coins"]
            if level_tag:
                value_parts.append(level_tag)
            fields.append(
                {
                    "name": f"{_rank_prefix(i)} {mention}",
                    "value": " · ".join(value_parts),
                    "inline": False,
                }
            )

        response = {
            "status": "ok",
            "action": req.action,
            "data": {"limit": limit, "count": len(fields)},
            "render": {
                "type": "embed",
                "title": "💰 BROski$ Rich List",
                "description": f"Top {len(fields)} coin holders in the HyperFocus Zone",
                "color": "#F1C40F",
                "fields": fields,
                "footer": "BROski Bot • HyperCode Core",
            },
        }
        _idempotency_store(
            idempotency_key=idempotency_key,
            request_hash=request_hash,
            action=req.action,
            response=response,
            db=db,
        )
        return response

    # ── leaderboard.xp ────────────────────────────────────────────────────────
    if req.action == "leaderboard.xp":
        try:
            limit = int(req.payload.get("limit", 10))
        except Exception:
            limit = 10
        limit = max(1, min(limit, 20))

        wallets = (
            db.query(BROskiWallet)
            .order_by(BROskiWallet.xp.desc())
            .limit(limit)
            .all()
        )
        fields = []
        for i, w in enumerate(wallets, start=1):
            u = db.query(models.User).filter(models.User.id == w.user_id).first()
            mention = f"<@{u.discord_id}>" if u and u.discord_id else f"User {w.user_id}"
            level_tag = f"Lvl {w.level} — {w.level_name}" if hasattr(w, "level") and w.level else ""
            value_parts = [f"**{w.xp:,}** XP"]
            if level_tag:
                value_parts.append(level_tag)
            fields.append(
                {
                    "name": f"{_rank_prefix(i)} {mention}",
                    "value": " · ".join(value_parts),
                    "inline": False,
                }
            )

        response = {
            "status": "ok",
            "action": req.action,
            "data": {"limit": limit, "count": len(fields)},
            "render": {
                "type": "embed",
                "title": "⚡ XP Leaderboard",
                "description": f"Top {len(fields)} grinders in the HyperFocus Zone",
                "color": "#9B59B6",
                "fields": fields,
                "footer": "BROski Bot • HyperCode Core",
            },
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
