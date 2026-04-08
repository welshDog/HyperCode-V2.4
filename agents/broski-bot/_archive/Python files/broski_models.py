"""
Database models using SQLAlchemy ORM.
Defines the database schema for users, economy, focus sessions, and quests.
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.database import Base


class QuestStatus(str, Enum):
    """Quest status enumeration."""
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    EXPIRED = "expired"


class User(Base):
    """User model representing Discord users."""
    
    __tablename__ = "users"
    
    # Primary key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    
    # Profile
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    discriminator: Mapped[str] = mapped_column(String(10), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))
    
    # Stats
    level: Mapped[int] = mapped_column(Integer, default=1)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    total_messages: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_seen: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    
    # Relationships
    economy: Mapped["Economy"] = relationship(
        "Economy",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    focus_sessions: Mapped[list["FocusSession"]] = relationship(
        "FocusSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    user_quests: Mapped[list["UserQuest"]] = relationship(
        "UserQuest",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<User {self.username}#{self.discriminator} (ID: {self.id})>"


class Economy(Base):
    """Economy model for user token balances and streaks."""
    
    __tablename__ = "economy"
    
    # Foreign key to user
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    
    # Balance
    balance: Mapped[int] = mapped_column(Integer, default=500)
    lifetime_earned: Mapped[int] = mapped_column(Integer, default=0)
    lifetime_spent: Mapped[int] = mapped_column(Integer, default=0)
    
    # Daily rewards
    last_daily_claim: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    daily_streak: Mapped[int] = mapped_column(Integer, default=0)
    max_daily_streak: Mapped[int] = mapped_column(Integer, default=0)
    
    # Memory crystals
    memory_crystals: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    
    # Relationships
    user: Mapped[User] = relationship("User", back_populates="economy")
    
    def __repr__(self) -> str:
        return f"<Economy user_id={self.user_id} balance={self.balance}>"


class FocusSession(Base):
    """Focus session model for tracking productivity sessions."""
    
    __tablename__ = "focus_sessions"
    
    # Primary key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    
    # Foreign key to user
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # Session details
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Rewards
    tokens_earned: Mapped[int] = mapped_column(Integer, default=0)
    is_hyperfocus: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    
    # Relationships
    user: Mapped[User] = relationship("User", back_populates="focus_sessions")
    
    def __repr__(self) -> str:
        status = "active" if self.is_active else "completed"
        return f"<FocusSession {self.project_name} ({status})>"


class Quest(Base):
    """Quest model for challenges and achievements."""
    
    __tablename__ = "quests"
    
    # Primary key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    
    # Quest details
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Requirements
    requirement_type: Mapped[str] = mapped_column(String(100), nullable=False)
    requirement_count: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Rewards
    token_reward: Mapped[int] = mapped_column(Integer, default=0)
    xp_reward: Mapped[int] = mapped_column(Integer, default=0)
    memory_crystal_reward: Mapped[int] = mapped_column(Integer, default=0)
    
    # Availability
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    
    # Relationships
    user_quests: Mapped[list["UserQuest"]] = relationship(
        "UserQuest",
        back_populates="quest",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<Quest {self.title}>"


class UserQuest(Base):
    """User quest progress model."""
    
    __tablename__ = "user_quests"
    
    # Primary key
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    
    # Foreign keys
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    quest_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("quests.id", ondelete="CASCADE"),
        nullable=False,
    )
    
    # Progress
    status: Mapped[QuestStatus] = mapped_column(
        SQLEnum(QuestStatus),
        default=QuestStatus.IN_PROGRESS,
    )
    progress: Mapped[int] = mapped_column(Integer, default=0)
    
    # Timestamps
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    user: Mapped[User] = relationship("User", back_populates="user_quests")
    quest: Mapped[Quest] = relationship("Quest", back_populates="user_quests")
    
    def __repr__(self) -> str:
        return f"<UserQuest user_id={self.user_id} quest_id={self.quest_id} status={self.status}>"
