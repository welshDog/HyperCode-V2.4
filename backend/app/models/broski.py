"""BROski$ Token System — ORM Models"""
from __future__ import annotations

import enum
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.base_class import Base


class TransactionType(str, enum.Enum):
    earn = "earn"
    spend = "spend"
    bonus = "bonus"


XP_LEVELS = [
    (0,    1, "BROski Recruit"),
    (100,  2, "BROski Cadet"),
    (250,  3, "BROski Agent"),
    (500,  4, "BROski Operator"),
    (1000, 5, "BROski Commander"),
    (2000, 6, "BROski Architect"),
    (5000, 7, "BROski Legend ♾️"),
]


def xp_to_level(xp: int) -> tuple[int, str]:
    """Return (level_number, level_name) for a given XP total."""
    current_level, current_name = 1, "BROski Recruit"
    for threshold, lvl, name in XP_LEVELS:
        if xp >= threshold:
            current_level, current_name = lvl, name
        else:
            break
    return current_level, current_name


class BROskiWallet(Base):
    __tablename__ = "broski_wallets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    coins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    level_name: Mapped[str] = mapped_column(String, default="BROski Recruit", nullable=False)
    last_daily_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_first_task_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    transactions: Mapped[list[BROskiTransaction]] = relationship(back_populates="wallet", cascade="all, delete-orphan")
    earned_achievements: Mapped[list[BROskiUserAchievement]] = relationship(back_populates="wallet", cascade="all, delete-orphan")


class BROskiTransaction(Base):
    __tablename__ = "broski_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    wallet_id: Mapped[int] = mapped_column(Integer, ForeignKey("broski_wallets.id"), nullable=False, index=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    meta: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    wallet: Mapped[BROskiWallet] = relationship(back_populates="transactions")


class BROskiAchievement(Base):
    __tablename__ = "broski_achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    xp_reward: Mapped[int] = mapped_column(Integer, default=0)
    coin_reward: Mapped[int] = mapped_column(Integer, default=0)
    icon: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    earned_by: Mapped[list[BROskiUserAchievement]] = relationship(back_populates="achievement")


class BROskiUserAchievement(Base):
    __tablename__ = "broski_user_achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    wallet_id: Mapped[int] = mapped_column(Integer, ForeignKey("broski_wallets.id"), nullable=False, index=True)
    achievement_slug: Mapped[str] = mapped_column(String(64), ForeignKey("broski_achievements.slug"), nullable=False)
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    wallet: Mapped[BROskiWallet] = relationship(back_populates="earned_achievements")
    achievement: Mapped[BROskiAchievement] = relationship(back_populates="earned_by")


class CourseSyncEvent(Base):
    """Idempotency log for Phase 2 Token Sync.

    Every award coming from the Course fires once and only once.
    The UNIQUE constraint on source_id is the last line of defence
    against double-counting — the app layer checks first, the DB enforces.
    """
    __tablename__ = "course_sync_events"
    __table_args__ = (UniqueConstraint("source_id", name="uq_course_sync_source_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    discord_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    tokens_awarded: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DiscordIdempotencyKey(Base):
    __tablename__ = "discord_idempotency_keys"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_discord_idempotency_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    response_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FocusSession(Base):
    __tablename__ = "focus_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    discord_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    baseline_ready: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    baseline_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    baseline_grade: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)
    baseline_counts: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    baseline_scanned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    end_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    end_grade: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)
    end_counts: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    end_scanned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    delta_available: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    delta_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    delta_counts: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    coins_awarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ModAction(Base):
    """Server Guardian moderation audit log. Feeds the weekly digest.

    Phase 3a writes status='auto_done' (reversible actions only).
    Phase 3c will use status='pending_veto' → 'executed'/'vetoed' for ban/kick.
    """
    __tablename__ = "mod_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    action_type: Mapped[str] = mapped_column(String(16), nullable=False)
    target_discord_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    target_username: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    severity: Mapped[str] = mapped_column(String(8), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    evidence: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="auto_done", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    executes_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class DailyMissionClaim(Base):
    __tablename__ = "daily_mission_claims"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "mission_date",
            "mission_slug",
            name="uq_daily_mission_claim_user_date_slug",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    mission_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    mission_slug: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    awarded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    coins_awarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    focus_session_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
