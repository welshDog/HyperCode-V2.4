from __future__ import annotations

import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal, get_db
from app.models import models
from app.models.broski import (
    BROskiTransaction,
    BROskiUserAchievement,
    BROskiWallet,
    DailyMissionClaim,
    DiscordIdempotencyKey,
    FocusSession,
    ModAction,
    TransactionType,
)
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
        "focus.start",
        "focus.stop",
        "focus.stats",
        "missions.today",
        "missions.claim",
        "codehealth.pulse",
        "digest.weekly",
        "mod.assess",
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


_FOCUS_WEIGHTS: dict[str, int] = {
    "critical": 100,
    "high": 30,
    "medium": 10,
    "low": 2,
}

_GRADE_RANK: dict[str, int] = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1}


def _grade_rank(grade: str | None) -> int:
    if not grade:
        return 0
    return _GRADE_RANK.get(str(grade).upper(), 0)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _nemoclaw_scan(*, targets: list[str] | None = None) -> dict[str, Any] | None:
    api_key = (settings.API_KEY or "").strip()
    if not api_key:
        return None

    url = str(settings.NEMOCLAW_URL).rstrip("/")
    timeout = float(settings.NEMOCLAW_TIMEOUT_SECONDS)
    body: dict[str, Any] = {}
    if targets:
        body["targets"] = targets

    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(
                f"{url}/scan",
                json=body,
                headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            )
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception:
        return None


def _nemoclaw_history(*, limit: int = 2) -> list[dict[str, Any]]:
    api_key = (settings.API_KEY or "").strip()
    if not api_key:
        return []
    url = str(settings.NEMOCLAW_URL).rstrip("/")
    timeout = float(settings.NEMOCLAW_TIMEOUT_SECONDS)
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(
                f"{url}/history",
                params={"limit": limit},
                headers={"X-API-Key": api_key},
            )
        if resp.status_code != 200:
            return []
        data = resp.json()
        scans = data.get("scans")
        return scans if isinstance(scans, list) else []
    except Exception:
        return []


def _pulse_decision(
    *,
    current: dict[str, Any],
    prior: dict[str, Any] | None,
    threshold: int,
) -> tuple[bool, str]:
    """Decide whether a code-health pulse is worth announcing."""
    if prior is None:
        return True, "baseline"
    cur_grade = str(current.get("grade") or "").upper()
    pri_grade = str(prior.get("grade") or "").upper()
    cur_score = _safe_int(current.get("score"))
    pri_score = _safe_int(prior.get("score"))

    if cur_grade != pri_grade:
        return True, "grade_up" if _grade_rank(cur_grade) > _grade_rank(pri_grade) else "grade_down"
    if abs(cur_score - pri_score) >= threshold:
        return True, "score_up" if cur_score > pri_score else "score_down"
    return False, "no_change"


def _render_pulse_embed(
    *,
    current: dict[str, Any],
    prior: dict[str, Any] | None,
    reason: str,
) -> dict[str, Any]:
    grade = str(current.get("grade") or "?").upper()
    score = _safe_int(current.get("score"))
    counts = current.get("counts") or {}
    files = _safe_int(current.get("total_files"))

    titles = {
        "baseline": ("🧠 NemoClaw baseline established", "#5865F2"),
        "grade_up": (f"📈 Code health climbing — Grade {grade}!", "#2ECC71"),
        "grade_down": (f"📉 Code health slipped — Grade {grade}", "#E67E22"),
        "score_up": (f"📈 Score up — Grade {grade} ({score}/100)", "#2ECC71"),
        "score_down": (f"📉 Score dipped — Grade {grade} ({score}/100)", "#E67E22"),
        "no_change": (f"🟰 Code health holding — Grade {grade}", "#5865F2"),
    }
    title, color = titles.get(reason, (f"🧠 Code health — Grade {grade}", "#5865F2"))

    if prior is not None:
        ps = _safe_int(prior.get("score"))
        pg = str(prior.get("grade") or "?").upper()
        delta = score - ps
        sign = f"+{delta}" if delta > 0 else str(delta)
        movement = f"{pg} {ps} → **{grade} {score}** ({sign})"
    else:
        movement = f"**{grade} {score}/100**"

    return {
        "type": "embed",
        "title": title,
        "description": movement,
        "color": color,
        "fields": [
            {
                "name": "Issue counts",
                "value": (
                    f"🆘 {counts.get('critical', 0)}  ·  "
                    f"⚠️ {counts.get('high', 0)}  ·  "
                    f"📌 {counts.get('medium', 0)}  ·  "
                    f"💡 {counts.get('low', 0)}"
                ),
                "inline": False,
            },
            {"name": "Files scanned", "value": str(files), "inline": True},
        ],
        "footer": "NemoClaw • autonomous pulse • chase the S 🏆",
    }


def _build_weekly_digest(*, db: Session, guild_member_count: int | None) -> dict[str, Any]:
    """Aggregate the last 7 days from existing tables. No new schema."""
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    # ── Economy (BROskiTransaction has created_at) ──
    txns = (
        db.query(BROskiTransaction)
        .filter(BROskiTransaction.created_at >= week_ago)
        .all()
    )
    earned = sum(
        t.amount for t in txns
        if t.type in (TransactionType.earn, TransactionType.bonus)
    )
    spent = sum(abs(t.amount) for t in txns if t.type == TransactionType.spend)

    per_wallet_earn: dict[int, int] = {}
    for t in txns:
        if t.type in (TransactionType.earn, TransactionType.bonus):
            per_wallet_earn[t.wallet_id] = per_wallet_earn.get(t.wallet_id, 0) + t.amount
    top_earners = sorted(per_wallet_earn.items(), key=lambda kv: kv[1], reverse=True)[:3]

    top_lines: list[str] = []
    for i, (wallet_id, amt) in enumerate(top_earners, start=1):
        wallet = db.query(BROskiWallet).filter(BROskiWallet.id == wallet_id).first()
        mention = f"User {wallet_id}"
        if wallet:
            u = db.query(models.User).filter(models.User.id == wallet.user_id).first()
            if u and u.discord_id:
                mention = f"<@{u.discord_id}>"
        top_lines.append(f"{_rank_prefix(i)} {mention} — **+{amt:,}**")

    # ── Focus (FocusSession.ended_at) ──
    sessions = (
        db.query(FocusSession)
        .filter(FocusSession.ended_at.isnot(None), FocusSession.ended_at >= week_ago)
        .all()
    )
    focus_minutes = sum(_safe_int(s.minutes) for s in sessions)
    focus_coins = sum(_safe_int(s.coins_awarded) for s in sessions)
    focus_users = len({s.user_id for s in sessions})
    best_jump = 0
    for s in sessions:
        if s.baseline_grade and s.end_grade:
            best_jump = max(best_jump, _grade_rank(s.end_grade) - _grade_rank(s.baseline_grade))

    # ── Missions + achievements + new members ──
    missions_done = (
        db.query(DailyMissionClaim)
        .filter(
            DailyMissionClaim.awarded.is_(True),
            DailyMissionClaim.claimed_at >= week_ago,
        )
        .count()
    )
    achievements = (
        db.query(BROskiUserAchievement)
        .filter(BROskiUserAchievement.earned_at >= week_ago)
        .count()
    )
    new_members = (
        db.query(BROskiWallet)
        .filter(BROskiWallet.created_at >= week_ago)
        .count()
    )
    total_linked = db.query(BROskiWallet).count()

    # ── Moderation incidents (7d) ──
    mod_rows = (
        db.query(ModAction)
        .filter(ModAction.created_at >= week_ago)
        .all()
    )
    incidents_total = len(mod_rows)
    if incidents_total:
        by_type: dict[str, int] = {}
        for m in mod_rows:
            by_type[m.action_type] = by_type.get(m.action_type, 0) + 1
        breakdown = " · ".join(f"{k}: **{v}**" for k, v in sorted(by_type.items()))
        incidents_value = f"**{incidents_total}** handled — {breakdown}"
    else:
        incidents_value = "**0** — all calm 🟢"

    # ── Code health trend (NemoClaw) ──
    history = _nemoclaw_history(limit=7)
    if history:
        cur = history[0]
        ch_line = f"Grade **{cur.get('grade', '?')}** · Score **{_safe_int(cur.get('score'))}/100**"
        if len(history) > 1:
            oldest = history[-1]
            ds = _safe_int(cur.get("score")) - _safe_int(oldest.get("score"))
            sign = f"+{ds}" if ds > 0 else str(ds)
            ch_line += f" · 7-scan trend {sign}"
    else:
        ch_line = "No scans on record"

    fields = [
        {
            "name": "👥 Community",
            "value": (
                f"Linked members: **{total_linked}**"
                + (f" · Server: **{guild_member_count}**" if guild_member_count else "")
                + f"\nNew this week: **{new_members}**"
            ),
            "inline": False,
        },
        {
            "name": "💰 Economy (7d)",
            "value": f"Earned: **+{earned:,}** · Spent: **−{spent:,}**",
            "inline": False,
        },
        {
            "name": "🏆 Top earners (7d)",
            "value": "\n".join(top_lines) if top_lines else "_No activity_",
            "inline": False,
        },
        {
            "name": "🎯 Focus (7d)",
            "value": (
                f"{len(sessions)} sessions · {focus_minutes} min · "
                f"{focus_users} BROskis · +{focus_coins:,} coins"
                + (f"\nBest grade jump: **+{best_jump}** ranks" if best_jump else "")
            ),
            "inline": False,
        },
        {
            "name": "📋 Engagement (7d)",
            "value": f"Missions claimed: **{missions_done}** · Achievements: **{achievements}**",
            "inline": False,
        },
        {
            "name": "🧠 Code health",
            "value": ch_line,
            "inline": False,
        },
        {
            "name": "🛡️ Incidents (7d)",
            "value": incidents_value,
            "inline": False,
        },
    ]

    return {
        "type": "embed",
        "title": "📊 BROski Weekly Digest",
        "description": f"Last 7 days · {week_ago.date()} → {now.date()}\nYou didn't log in. BROski ran it. 🐶♾️",
        "color": "#9B59B6",
        "fields": fields,
        "footer": "BROski Server Guardian • weekly digest",
    }


def _baseline_scan_task(*, session_id: int) -> None:
    scan = _nemoclaw_scan()
    if not scan:
        return

    db = SessionLocal()
    try:
        sess = db.query(FocusSession).filter(FocusSession.id == session_id).first()
        if not sess or sess.baseline_ready:
            return

        sess.baseline_ready = True
        sess.baseline_score = _safe_int(scan.get("score"))
        sess.baseline_grade = str(scan.get("grade") or "").upper() or None
        sess.baseline_counts = scan.get("counts") or {}
        sess.baseline_scanned_at = datetime.now(timezone.utc)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _compute_focus_reward(
    *,
    baseline: dict[str, int],
    end: dict[str, int],
    baseline_grade: str | None,
    end_grade: str | None,
    baseline_score: int,
    end_score: int,
) -> tuple[int, dict[str, int], dict[str, int]]:
    delta: dict[str, int] = {}
    fixed: dict[str, int] = {}
    for k in ("critical", "high", "medium", "low"):
        b = _safe_int(baseline.get(k))
        e = _safe_int(end.get(k))
        delta[k] = e - b
        fixed[k] = max(0, b - e)

    if end_score < baseline_score:
        return 0, delta, fixed

    coins = 0
    for k, w in _FOCUS_WEIGHTS.items():
        coins += fixed.get(k, 0) * w

    if _grade_rank(end_grade) > _grade_rank(baseline_grade):
        coins += 50

    if str(baseline_grade or "").upper() == "S" and str(end_grade or "").upper() == "S":
        coins += 25

    return coins, delta, fixed


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
    background_tasks: BackgroundTasks,
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

    # ── codehealth.pulse (system action — no user lookup) ────────────────────
    if req.action == "codehealth.pulse":
        scan = _nemoclaw_scan()
        if not scan:
            response = {
                "status": "ok",
                "action": req.action,
                "data": {"should_post": False, "reason": "scan_unavailable"},
                "render": _render_info_embed(
                    title="⚠️ NemoClaw scan unavailable",
                    description="Pulse skipped — agent offline or busy.",
                    color="#FEE75C",
                ),
            }
        else:
            history = _nemoclaw_history(limit=2)
            # history[0] is the scan we just ran; history[1] is the prior one
            prior = history[1] if len(history) >= 2 else None
            threshold = int(settings.CODE_HEALTH_PULSE_THRESHOLD)
            should_post, reason = _pulse_decision(
                current=scan, prior=prior, threshold=threshold
            )
            response = {
                "status": "ok",
                "action": req.action,
                "data": {
                    "should_post": should_post,
                    "reason": reason,
                    "scan_id": scan.get("scan_id"),
                    "grade": scan.get("grade"),
                    "score": scan.get("score"),
                },
                "render": _render_pulse_embed(
                    current=scan, prior=prior, reason=reason
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

    # ── digest.weekly (system action — no user lookup) ───────────────────────
    if req.action == "digest.weekly":
        try:
            gmc = req.payload.get("guild_member_count")
            gmc_int = int(gmc) if gmc is not None else None
        except (TypeError, ValueError):
            gmc_int = None

        render = _build_weekly_digest(db=db, guild_member_count=gmc_int)
        response = {
            "status": "ok",
            "action": req.action,
            "data": {"generated_at": datetime.now(timezone.utc).isoformat()},
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

    # ── mod.assess (system action — Phase 3a, reversible only) ───────────────
    if req.action == "mod.assess":
        kind = str(req.payload.get("kind") or "").strip()
        target_id = str(req.payload.get("target_discord_id") or "").strip()
        target_name = str(req.payload.get("target_username") or "")[:128] or None
        evidence = req.payload.get("evidence")
        if not isinstance(evidence, dict):
            evidence = {}

        if kind not in {"spam", "blocklist"}:
            response = {
                "status": "ok",
                "action": req.action,
                "data": {"directive": "none", "reason": "unknown_kind"},
                "render": _render_info_embed(
                    title="🛡️ No action",
                    description="Unrecognised moderation kind.",
                    color="#FEE75C",
                ),
            }
        elif not target_id:
            response = {
                "status": "ok",
                "action": req.action,
                "data": {"directive": "none", "reason": "no_target"},
                "render": _render_info_embed(
                    title="🛡️ No action",
                    description="No target supplied.",
                    color="#FEE75C",
                ),
            }
        else:
            # Phase 3a caps at a reversible timeout + message delete.
            # Ban/kick (severe) is deliberately NOT producible here — Phase 3c.
            severity = "medium"
            timeout_seconds = int(settings.MOD_DEFAULT_TIMEOUT_SECONDS)
            reason = (
                "Spam burst auto-handled"
                if kind == "spam"
                else "Blocklisted content auto-handled"
            )

            row = ModAction(
                action_type="timeout",
                target_discord_id=target_id,
                target_username=target_name,
                severity=severity,
                reason=reason,
                evidence={"kind": kind, **evidence},
                status="auto_done",
                resolved_at=datetime.now(timezone.utc),
            )
            db.add(row)
            db.commit()
            db.refresh(row)

            response = {
                "status": "ok",
                "action": req.action,
                "data": {
                    "directive": "timeout",
                    "timeout_seconds": timeout_seconds,
                    "delete_message": True,
                    "severity": severity,
                    "reason": reason,
                    "mod_action_id": row.id,
                },
                "render": _render_info_embed(
                    title="🛡️ Auto-mod applied",
                    description=(
                        f"<@{target_id}> · {reason}\n"
                        f"Timeout: {timeout_seconds // 60} min · message removed"
                    ),
                    color="#E67E22",
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

    if req.action == "focus.start":
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
            active = (
                db.query(FocusSession)
                .filter(FocusSession.discord_id == discord_id, FocusSession.ended_at.is_(None))
                .order_by(FocusSession.started_at.desc())
                .first()
            )
            if active:
                response = {
                    "status": "ok",
                    "action": req.action,
                    "data": {
                        "session_id": active.id,
                        "baseline_status": "ready" if active.baseline_ready else "pending",
                    },
                    "render": _render_info_embed(
                        title="🎯 Focus already running",
                        description="Session is already active. Use `/focus stop` when done.",
                        color="#FEE75C",
                    ),
                }
            else:
                sess = FocusSession(
                    user_id=user.id,
                    discord_id=discord_id,
                    started_at=datetime.now(timezone.utc),
                    baseline_ready=False,
                    coins_awarded=0,
                    delta_available=False,
                )
                db.add(sess)
                db.commit()
                db.refresh(sess)
                background_tasks.add_task(_baseline_scan_task, session_id=sess.id)
                response = {
                    "status": "ok",
                    "action": req.action,
                    "data": {"session_id": sess.id, "baseline_status": "pending"},
                    "render": _render_info_embed(
                        title="🎯 Session locked in",
                        description="Baselining in background. Crush the session.",
                        color="#E67E22",
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

    if req.action == "focus.stop":
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
            sess = (
                db.query(FocusSession)
                .filter(FocusSession.discord_id == discord_id, FocusSession.ended_at.is_(None))
                .order_by(FocusSession.started_at.desc())
                .first()
            )
            if not sess:
                response = {
                    "status": "ok",
                    "action": req.action,
                    "data": {"ok": False},
                    "render": _render_info_embed(
                        title="❌ No active focus session",
                        description="Start one with `/focus start`.",
                        color="#ED4245",
                    ),
                }
            else:
                now = datetime.now(timezone.utc)
                started = sess.started_at
                if started.tzinfo is None:
                    started = started.replace(tzinfo=timezone.utc)
                minutes = max(1, int((now - started).total_seconds() / 60))
                sess.ended_at = now
                sess.minutes = minutes

                min_minutes = int(settings.FOCUS_MIN_MINUTES)
                if minutes < min_minutes:
                    sess.delta_available = False
                    sess.coins_awarded = 0
                    db.commit()
                    response = {
                        "status": "ok",
                        "action": req.action,
                        "data": {
                            "session_id": sess.id,
                            "minutes": minutes,
                            "delta_available": False,
                            "coins_awarded": 0,
                        },
                        "render": _render_info_embed(
                            title="💪 Short session logged",
                            description="Focus longer for code rewards.",
                            color="#FEE75C",
                        ),
                    }
                elif not sess.baseline_ready or not sess.baseline_counts:
                    sess.delta_available = False
                    sess.coins_awarded = 0
                    db.commit()
                    response = {
                        "status": "ok",
                        "action": req.action,
                        "data": {
                            "session_id": sess.id,
                            "minutes": minutes,
                            "delta_available": False,
                            "coins_awarded": 0,
                        },
                        "render": _render_info_embed(
                            title="✅ Session logged",
                            description="Baseline still running. No delta this round.",
                            color="#5865F2",
                        ),
                    }
                else:
                    scan = _nemoclaw_scan()
                    if not scan:
                        sess.delta_available = False
                        sess.coins_awarded = 0
                        db.commit()
                        response = {
                            "status": "ok",
                            "action": req.action,
                            "data": {
                                "session_id": sess.id,
                                "minutes": minutes,
                                "delta_available": False,
                                "coins_awarded": 0,
                            },
                            "render": _render_info_embed(
                                title="⚠️ Scan unavailable",
                                description="Focus logged. Try again later for delta.",
                                color="#FEE75C",
                            ),
                        }
                    else:
                        end_counts = scan.get("counts") or {}
                        end_score = _safe_int(scan.get("score"))
                        end_grade = str(scan.get("grade") or "").upper() or None
                        base_counts = sess.baseline_counts or {}
                        base_score = _safe_int(sess.baseline_score)
                        base_grade = sess.baseline_grade

                        coins, delta_counts, _fixed = _compute_focus_reward(
                            baseline=base_counts,
                            end=end_counts,
                            baseline_grade=base_grade,
                            end_grade=end_grade,
                            baseline_score=base_score,
                            end_score=end_score,
                        )

                        sess.end_score = end_score
                        sess.end_grade = end_grade
                        sess.end_counts = end_counts
                        sess.end_scanned_at = datetime.now(timezone.utc)
                        sess.delta_available = True
                        sess.delta_score = end_score - base_score
                        sess.delta_counts = delta_counts

                        awarded = 0
                        if coins > 0:
                            wallet = broski_service.award_coins(
                                user_id=user.id,
                                amount=coins,
                                reason="Focus code delta",
                                db=db,
                                meta={
                                    "source": "focus",
                                    "session_id": sess.id,
                                    "discord_id": discord_id,
                                },
                            )
                            awarded = coins
                            _ = wallet

                        sess.coins_awarded = awarded
                        db.commit()
                        response = {
                            "status": "ok",
                            "action": req.action,
                            "data": {
                                "session_id": sess.id,
                                "minutes": minutes,
                                "delta_available": True,
                                "coins_awarded": awarded,
                            },
                            "render": _render_info_embed(
                                title="🏆 Focus complete",
                                description=f"Minutes: {minutes}  ·  Coins: +{awarded}",
                                color="#2ECC71",
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

    if req.action == "focus.stats":
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
            ended = (
                db.query(FocusSession)
                .filter(FocusSession.user_id == user.id, FocusSession.ended_at.isnot(None))
                .order_by(FocusSession.ended_at.desc())
                .all()
            )

            min_minutes = int(settings.FOCUS_MIN_MINUTES)
            now = datetime.now(timezone.utc).date()
            days: set = set()
            total_minutes = 0
            total_minutes_7d = 0
            coins_total = 0
            best_grade_rank = 0
            best_grade_at: str | None = None
            best_jump = 0
            streak = 0

            for s in ended:
                m = _safe_int(s.minutes)
                coins_total += _safe_int(s.coins_awarded)
                if s.end_grade:
                    r = _grade_rank(s.end_grade)
                    if r > best_grade_rank and s.ended_at is not None:
                        best_grade_rank = r
                        best_grade_at = s.ended_at.isoformat()

                if s.baseline_grade and s.end_grade:
                    jump = _grade_rank(s.end_grade) - _grade_rank(s.baseline_grade)
                    best_jump = max(best_jump, jump)

                if m <= 0:
                    continue
                total_minutes += m
                if s.ended_at is not None:
                    d = s.ended_at.date()
                    if (now - d).days <= 6:
                        total_minutes_7d += m
                    if m >= min_minutes:
                        days.add(d)

            cur = now
            while cur in days:
                streak += 1
                cur = cur - timedelta(days=1)

            best_grade = None
            for g, r in _GRADE_RANK.items():
                if r == best_grade_rank:
                    best_grade = g
                    break

            response = {
                "status": "ok",
                "action": req.action,
                "data": {
                    "minutes_7d": total_minutes_7d,
                    "minutes_all_time": total_minutes,
                    "coins_from_focus": coins_total,
                    "best_grade_jump": best_jump,
                    "streak_days": streak,
                    "best_grade": best_grade,
                    "best_grade_at": best_grade_at,
                },
                "render": _render_info_embed(
                    title="📊 Focus stats",
                    description=f"7d: {total_minutes_7d}m  ·  all: {total_minutes}m",
                    color="#9B59B6",
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

    if req.action == "missions.today":
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
            mission_date = datetime.now(timezone.utc).date()
            day_start = datetime(
                mission_date.year,
                mission_date.month,
                mission_date.day,
                tzinfo=timezone.utc,
            )
            day_end = day_start + timedelta(days=1)
            min_minutes = int(settings.FOCUS_MIN_MINUTES)

            qualifying = (
                db.query(FocusSession)
                .filter(
                    FocusSession.user_id == user.id,
                    FocusSession.ended_at.isnot(None),
                    FocusSession.ended_at >= day_start,
                    FocusSession.ended_at < day_end,
                    FocusSession.minutes >= min_minutes,
                )
                .order_by(FocusSession.ended_at.desc())
                .first()
            )

            claim = (
                db.query(DailyMissionClaim)
                .filter(
                    DailyMissionClaim.user_id == user.id,
                    DailyMissionClaim.mission_date == mission_date,
                    DailyMissionClaim.mission_slug == "focus_block",
                )
                .first()
            )

            claimed = bool(claim and claim.awarded)
            claimable = bool(qualifying and not claimed)
            reward = 50
            status = "✅ Claimable" if claimable else ("🏁 Claimed" if claimed else "⏳ Not yet")

            response = {
                "status": "ok",
                "action": req.action,
                "data": {
                    "date": str(mission_date),
                    "focus_block": {
                        "slug": "focus_block",
                        "reward_coins": reward,
                        "qualifying": bool(qualifying),
                        "claimable": claimable,
                        "claimed": claimed,
                    },
                },
                "render": {
                    "type": "embed",
                    "title": "📋 Missions — Today",
                    "description": f"Focus Block: {status}",
                    "color": "#F39C12",
                    "fields": [
                        {
                            "name": "🎯 Focus Block",
                            "value": f"Do ≥ {min_minutes} min focus today.\nReward: **{reward}** BROski$",
                            "inline": False,
                        }
                    ],
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

    if req.action == "missions.claim":
        user = db.query(models.User).filter(models.User.discord_id == discord_id).first()
        slug = str(req.payload.get("slug") or "").strip()
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
        elif slug != "focus_block":
            response = {
                "status": "ok",
                "action": req.action,
                "data": {"awarded": False, "reason": "invalid_slug"},
                "render": _render_info_embed(
                    title="❌ Unknown mission",
                    description="Only 'focus_block' is supported right now.",
                    color="#ED4245",
                ),
            }
        else:
            mission_date = datetime.now(timezone.utc).date()
            day_start = datetime(
                mission_date.year,
                mission_date.month,
                mission_date.day,
                tzinfo=timezone.utc,
            )
            day_end = day_start + timedelta(days=1)
            min_minutes = int(settings.FOCUS_MIN_MINUTES)
            reward = 50

            qualifying = (
                db.query(FocusSession)
                .filter(
                    FocusSession.user_id == user.id,
                    FocusSession.ended_at.isnot(None),
                    FocusSession.ended_at >= day_start,
                    FocusSession.ended_at < day_end,
                    FocusSession.minutes >= min_minutes,
                )
                .order_by(FocusSession.ended_at.desc())
                .first()
            )

            existing = (
                db.query(DailyMissionClaim)
                .filter(
                    DailyMissionClaim.user_id == user.id,
                    DailyMissionClaim.mission_date == mission_date,
                    DailyMissionClaim.mission_slug == "focus_block",
                )
                .with_for_update()
                .first()
            )

            if existing and existing.awarded:
                response = {
                    "status": "ok",
                    "action": req.action,
                    "data": {"awarded": False, "already_claimed": True},
                    "render": _render_info_embed(
                        title="🏁 Already claimed",
                        description="You already claimed Focus Block today.",
                        color="#57F287",
                    ),
                }
            elif not qualifying:
                response = {
                    "status": "ok",
                    "action": req.action,
                    "data": {"awarded": False, "eligible": False},
                    "render": _render_info_embed(
                        title="⏳ Not eligible yet",
                        description=f"Complete a focus session of ≥ {min_minutes} minutes today first.",
                        color="#FEE75C",
                    ),
                }
            else:
                if not existing:
                    existing = DailyMissionClaim(
                        user_id=user.id,
                        mission_date=mission_date,
                        mission_slug="focus_block",
                        awarded=False,
                        coins_awarded=0,
                        focus_session_id=qualifying.id,
                    )
                    db.add(existing)
                    try:
                        db.commit()
                        db.refresh(existing)
                    except IntegrityError:
                        db.rollback()
                        existing = (
                            db.query(DailyMissionClaim)
                            .filter(
                                DailyMissionClaim.user_id == user.id,
                                DailyMissionClaim.mission_date == mission_date,
                                DailyMissionClaim.mission_slug == "focus_block",
                            )
                            .first()
                        )

                awarded = False
                coins_awarded = 0
                if existing and not existing.awarded:
                    _ = broski_service.award_coins(
                        user_id=user.id,
                        amount=reward,
                        reason="Daily mission: Focus Block",
                        db=db,
                        meta={
                            "source": "mission",
                            "slug": "focus_block",
                            "date": str(mission_date),
                            "focus_session_id": qualifying.id,
                        },
                    )
                    existing.awarded = True
                    existing.coins_awarded = reward
                    existing.focus_session_id = qualifying.id
                    db.commit()
                    awarded = True
                    coins_awarded = reward

                response = {
                    "status": "ok",
                    "action": req.action,
                    "data": {
                        "awarded": awarded,
                        "coins_awarded": coins_awarded,
                        "mission_slug": "focus_block",
                    },
                    "render": _render_info_embed(
                        title="🏆 Mission complete!",
                        description=f"+{coins_awarded} BROski$",
                        color="#57F287",
                    )
                    if awarded
                    else _render_info_embed(
                        title="🏁 Already claimed",
                        description="You already claimed Focus Block today.",
                        color="#57F287",
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
