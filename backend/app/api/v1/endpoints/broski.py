"""BROski$ Token System — API Endpoints"""
from __future__ import annotations

from typing import Any

import redis
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import models
from app.models.broski import BROskiAchievement
from app.schemas.broski import (
    WalletResponse,
    TransactionPage,
    AchievementResponse,
    UserAchievementResponse,
    LeaderboardEntry,
    AwardRequest,
)
from app.services import broski_service
from app.api import deps

router = APIRouter()


@router.get("/wallet", response_model=WalletResponse)
def get_my_wallet(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """Get your BROski$ wallet — coins, XP, and level."""
    wallet = broski_service.get_wallet(current_user.id, db)
    return wallet


@router.get("/transactions", response_model=TransactionPage)
def get_my_transactions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> Any:
    """Get your full BROski$ transaction history."""
    items, total = broski_service.get_transactions(current_user.id, db, skip=skip, limit=limit)
    return TransactionPage(items=items, total=total, skip=skip, limit=limit)


@router.get("/achievements", response_model=list[AchievementResponse])
def list_achievements(
    db: Session = Depends(get_db),
    _: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """List ALL available achievements you can unlock."""
    return db.query(BROskiAchievement).all()


@router.get("/achievements/me", response_model=list[UserAchievementResponse])
def get_my_achievements(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """See which achievements YOU'VE earned. 🏆"""
    wallet = broski_service.get_wallet(current_user.id, db)
    return wallet.earned_achievements


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
def get_leaderboard(
    db: Session = Depends(get_db),
    _: models.User = Depends(deps.get_current_active_user),
    limit: int = Query(10, ge=1, le=50),
) -> Any:
    """Top BROski$ earners — where do you rank? 🏅"""
    return broski_service.get_leaderboard(db, limit=limit)


@router.post("/award")
def award_coins_and_xp(
    award: AwardRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """Admin/agent endpoint — award coins and/or XP to a user."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403,
            detail="Only admins and agents can award BROski$ coins directly.",
        )

    level_up_msg = None
    wallet = None

    if award.coins > 0:
        wallet = broski_service.award_coins(award.user_id, award.coins, award.reason, db)

    if award.xp > 0:
        wallet, level_up_msg = broski_service.award_xp(award.user_id, award.xp, award.reason, db)

    if wallet is None:
        wallet = broski_service.get_wallet(award.user_id, db)

    response: dict[str, Any] = {
        "message": f"BROski$ awarded! +{award.coins} coins, +{award.xp} XP ⚡",
        "wallet": WalletResponse.model_validate(wallet),
    }
    if level_up_msg:
        response["level_up"] = level_up_msg

    return response


@router.get("/pulse")
def get_broski_pulse(db: Session = Depends(get_db)) -> Any:
    """Public system-wide BROski$ pulse — no auth needed. Used by dashboard."""
    from app.models.broski import BROskiWallet
    from app.core.config import settings as cfg

    total_coins = db.query(func.sum(BROskiWallet.coins)).scalar() or 0
    total_xp = db.query(func.sum(BROskiWallet.xp)).scalar() or 0
    user_count = db.query(func.count(BROskiWallet.id)).scalar() or 0

    # Count agents online via Redis heartbeats
    agents_online = 0
    try:
        r = redis.Redis.from_url(cfg.HYPERCODE_REDIS_URL, decode_responses=True, socket_connect_timeout=1)
        keys = r.keys("agents:heartbeat:*")
        agents_online = len(keys)
        r.close()
    except Exception:
        pass

    from app.models.broski import xp_to_level
    total_xp_int = int(total_xp)
    level, level_name = xp_to_level(total_xp_int)

    return {
        "coins": int(total_coins),
        "xp": total_xp_int,
        "level": level,
        "level_name": level_name,
        "agentsOnline": agents_online,
        "userCount": int(user_count),
    }


@router.post("/daily-login")
def daily_login(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
) -> Any:
    """Claim your daily login bonus — +5 coins, once every 24 hours!"""
    wallet, awarded = broski_service.handle_daily_login(current_user.id, db)
    if awarded:
        return {
            "message": "Daily login bonus claimed! +5 BROski$ coins 📅",
            "wallet": WalletResponse.model_validate(wallet),
        }
    return {
        "message": "Already claimed today — come back tomorrow for more coins! ⏰",
        "wallet": WalletResponse.model_validate(wallet),
    }
