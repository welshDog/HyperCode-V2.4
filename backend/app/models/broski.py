"""BROski$ Token System — ORM Models"""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, JSON
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
