"""BROski$ Token System — Pydantic v2 Schemas"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Any

from pydantic import BaseModel, ConfigDict

from app.models.broski import TransactionType


# ── Wallet ────────────────────────────────────────────────────────────
class WalletResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    coins: int
    xp: int
    level: int
    level_name: str
    created_at: datetime
    updated_at: Optional[datetime] = None


# ── Transaction ───────────────────────────────────────────────────────
class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    wallet_id: int
    amount: int
    type: TransactionType
    reason: str
    meta: Optional[Any] = None
    created_at: datetime


class TransactionPage(BaseModel):
    items: list[TransactionResponse]
    total: int
    skip: int
    limit: int


# ── Achievement ───────────────────────────────────────────────────────
class AchievementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    description: str
    xp_reward: int
    coin_reward: int
    icon: Optional[str] = None


class UserAchievementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    achievement_slug: str
    earned_at: datetime
    achievement: AchievementResponse


# ── Award Request (admin / agent endpoint) ────────────────────────────
class AwardRequest(BaseModel):
    user_id: int
    coins: int = 0
    xp: int = 0
    reason: str


# ── Leaderboard ───────────────────────────────────────────────────────
class LeaderboardEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    coins: int
    xp: int
    level: int
    level_name: str
