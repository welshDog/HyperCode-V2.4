"""BROski$ Token System — Business Logic Service"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models.broski import (
    BROskiWallet,
    BROskiTransaction,
    BROskiAchievement,
    BROskiUserAchievement,
    TransactionType,
    xp_to_level,
)

logger = logging.getLogger(__name__)

# ── Seed data ─────────────────────────────────────────────────────────
SEED_ACHIEVEMENTS = [
    {
        "slug": "first_blood",
        "name": "First Blood 🩸",
        "description": "Complete your very first task — you're off! 🚀",
        "xp_reward": 50,
        "coin_reward": 20,
        "icon": "🩸",
    },
    {
        "slug": "streak_3",
        "name": "On a Roll 🔥",
        "description": "Complete 3 tasks in a single day — momentum unlocked!",
        "xp_reward": 100,
        "coin_reward": 30,
        "icon": "🔥",
    },
    {
        "slug": "mission_launch",
        "name": "Mission Launched 🚀",
        "description": "Start your first mission — let's go!",
        "xp_reward": 75,
        "coin_reward": 25,
        "icon": "🚀",
    },
    {
        "slug": "hyperfocus_hero",
        "name": "Hyperfocus Hero 🦅",
        "description": "Complete 5 tasks in one session — absolute beast mode!",
        "xp_reward": 150,
        "coin_reward": 50,
        "icon": "🦅",
    },
    {
        "slug": "early_bird",
        "name": "Early Bird ☀️",
        "description": "Complete a task before 9 AM — rise and grind!",
        "xp_reward": 30,
        "coin_reward": 10,
        "icon": "☀️",
    },
]


def seed_achievements(db: Session) -> None:
    """Insert seed achievements if they don't exist yet."""
    for data in SEED_ACHIEVEMENTS:
        exists = db.query(BROskiAchievement).filter_by(slug=data["slug"]).first()
        if not exists:
            db.add(BROskiAchievement(**data))
    db.commit()


# ── Wallet helpers ────────────────────────────────────────────────────
def _get_or_create_wallet(user_id: int, db: Session) -> BROskiWallet:
    wallet = db.query(BROskiWallet).filter_by(user_id=user_id).first()
    if not wallet:
        wallet = BROskiWallet(user_id=user_id)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
        logger.info("🆕 BROski$ wallet created for user %s", user_id)
    return wallet


def _log_transaction(
    wallet: BROskiWallet,
    amount: int,
    tx_type: TransactionType,
    reason: str,
    db: Session,
    meta: Optional[dict] = None,
) -> BROskiTransaction:
    tx = BROskiTransaction(
        wallet_id=wallet.id,
        amount=amount,
        type=tx_type,
        reason=reason,
        meta=meta,
    )
    db.add(tx)
    return tx


def _check_level_up(wallet: BROskiWallet) -> Optional[str]:
    new_level, new_name = xp_to_level(wallet.xp)
    if new_level != wallet.level:
        wallet.level = new_level
        wallet.level_name = new_name
        msg = f"LEVEL UP BROski! You're now a {new_name}! 🔥"
        logger.info("🎉 %s — user %s", msg, wallet.user_id)
        return msg
    return None


# ── Public API ────────────────────────────────────────────────────────
def get_wallet(user_id: int, db: Session) -> BROskiWallet:
    return _get_or_create_wallet(user_id, db)


def award_coins(
    user_id: int,
    amount: int,
    reason: str,
    db: Session,
    meta: Optional[dict] = None,
) -> BROskiWallet:
    wallet = _get_or_create_wallet(user_id, db)
    wallet.coins += amount
    _log_transaction(wallet, amount, TransactionType.earn, reason, db, meta)
    db.commit()
    db.refresh(wallet)
    logger.info("🔥 BROski$ awarded: +%d coins to user %s (%s)", amount, user_id, reason)
    return wallet


def award_xp(
    user_id: int,
    amount: int,
    reason: str,
    db: Session,
    meta: Optional[dict] = None,
) -> tuple[BROskiWallet, Optional[str]]:
    """Returns (wallet, level_up_message_or_None)."""
    wallet = _get_or_create_wallet(user_id, db)
    wallet.xp += amount
    _log_transaction(wallet, amount, TransactionType.earn, f"XP: {reason}", db, meta)
    level_up_msg = _check_level_up(wallet)
    db.commit()
    db.refresh(wallet)
    logger.info("⚡ BROski$ XP awarded: +%d xp to user %s (%s)", amount, user_id, reason)
    return wallet, level_up_msg


def spend_coins(
    user_id: int,
    amount: int,
    reason: str,
    db: Session,
    meta: Optional[dict] = None,
) -> BROskiWallet:
    wallet = _get_or_create_wallet(user_id, db)
    if wallet.coins < amount:
        shortfall = amount - wallet.coins
        raise ValueError(
            f"Not enough BROski$ coins — you need {shortfall} more! 💸"
        )
    wallet.coins -= amount
    _log_transaction(wallet, -amount, TransactionType.spend, reason, db, meta)
    db.commit()
    db.refresh(wallet)
    logger.info("💸 BROski$ spent: -%d coins from user %s (%s)", amount, user_id, reason)
    return wallet


def get_transactions(
    user_id: int,
    db: Session,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[BROskiTransaction], int]:
    wallet = _get_or_create_wallet(user_id, db)
    q = db.query(BROskiTransaction).filter_by(wallet_id=wallet.id)
    total = q.count()
    items = q.order_by(BROskiTransaction.created_at.desc()).offset(skip).limit(limit).all()
    return items, total


def check_and_award_achievements(
    user_id: int,
    db: Session,
    context: Optional[dict] = None,
) -> list[str]:
    """Evaluate achievements and award any not yet earned. Returns list of unlock messages."""
    wallet = _get_or_create_wallet(user_id, db)
    context = context or {}
    unlocked: list[str] = []

    earned_slugs = {
        ua.achievement_slug for ua in wallet.earned_achievements
    }

    def _unlock(slug: str) -> None:
        if slug in earned_slugs:
            return
        achievement = db.query(BROskiAchievement).filter_by(slug=slug).first()
        if not achievement:
            return
        ua = BROskiUserAchievement(wallet_id=wallet.id, achievement_slug=slug)
        db.add(ua)
        wallet.coins += achievement.coin_reward
        wallet.xp += achievement.xp_reward
        _log_transaction(
            wallet, achievement.coin_reward, TransactionType.bonus,
            f"Achievement: {achievement.name}", db,
        )
        _check_level_up(wallet)
        db.commit()
        db.refresh(wallet)
        earned_slugs.add(slug)
        msg = f"Achievement unlocked: {achievement.name}! {achievement.description} 🏆"
        unlocked.append(msg)
        logger.info("🏆 %s — user %s", msg, user_id)

    # first_blood — has completed at least 1 task
    if context.get("tasks_completed_total", 0) >= 1:
        _unlock("first_blood")

    # streak_3 — 3+ tasks completed today
    if context.get("tasks_completed_today", 0) >= 3:
        _unlock("streak_3")

    # mission_launch — has started a mission
    if context.get("missions_started_total", 0) >= 1:
        _unlock("mission_launch")

    # hyperfocus_hero — 5+ tasks in session
    if context.get("tasks_completed_session", 0) >= 5:
        _unlock("hyperfocus_hero")

    # early_bird — task completed before 9 AM today
    if context.get("completed_before_9am", False):
        _unlock("early_bird")

    return unlocked


def get_leaderboard(db: Session, limit: int = 10) -> list[BROskiWallet]:
    return (
        db.query(BROskiWallet)
        .order_by(BROskiWallet.coins.desc(), BROskiWallet.xp.desc())
        .limit(limit)
        .all()
    )


def handle_daily_login(user_id: int, db: Session) -> tuple[BROskiWallet, bool]:
    """Award 5 coins for daily login (once per 24h). Returns (wallet, awarded_bool)."""
    wallet = _get_or_create_wallet(user_id, db)
    now = datetime.now(timezone.utc)
    last = wallet.last_daily_login
    # Normalise to aware datetime regardless of DB backend (SQLite stores naive)
    if last is not None and last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    if last and (now - last) < timedelta(hours=24):
        return wallet, False
    wallet.last_daily_login = now
    wallet.coins += 5
    _log_transaction(wallet, 5, TransactionType.earn, "Daily login bonus", db)
    db.commit()
    db.refresh(wallet)
    logger.info("📅 Daily login bonus +5 coins for user %s", user_id)
    return wallet, True
