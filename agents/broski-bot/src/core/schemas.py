"""
Data transfer objects (DTOs) for the application.
Provides type-safe models for API and service layer responses.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class UserBase(BaseModel):
    """Base user model."""
    id: int = Field(..., description="Discord user ID")
    username: str = Field(..., description="Discord username")
    discriminator: str = Field(..., description="Discord discriminator")
    avatar_url: Optional[str] = Field(None, description="Discord avatar URL")

    model_config = ConfigDict(from_attributes=True)


class UserProfile(UserBase):
    """User profile with stats."""
    level: int = Field(default=1)
    xp: int = Field(default=0)
    total_messages: int = Field(default=0)
    created_at: datetime
    updated_at: datetime
    last_seen: datetime


class EconomyBase(BaseModel):
    """Base economy model."""
    user_id: int = Field(..., description="Discord user ID")
    balance: int = Field(default=500)
    
    model_config = ConfigDict(from_attributes=True)


class EconomyProfile(EconomyBase):
    """Full economy profile with streaks."""
    lifetime_earned: int = Field(default=0)
    lifetime_spent: int = Field(default=0)
    last_daily_claim: Optional[datetime] = None
    daily_streak: int = Field(default=0)
    max_daily_streak: int = Field(default=0)
    memory_crystals: int = Field(default=0)
    created_at: datetime
    updated_at: datetime


class FocusSessionBase(BaseModel):
    """Base focus session model."""
    id: int
    user_id: int
    project_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    tokens_earned: int = 0
    is_hyperfocus: bool = False
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class FocusSessionProfile(FocusSessionBase):
    """Full focus session profile."""
    created_at: datetime
