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


class QuestType(str, Enum):
    """Quest type enumeration."""
    STANDARD = "standard"
    TIMED = "timed"
    COLLABORATIVE = "collaborative"
    TIERED = "tiered"

class QuestStatus(str, Enum):
    """Quest status enumeration."""
    AVAILABLE = "available"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
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
    user_achievements: Mapped[list["UserAchievement"]] = relationship(
        "UserAchievement",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
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


class Transaction(Base):
    """Transaction model for economy ledger."""
    
    __tablename__ = "transactions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False) # credit, debit
    category: Mapped[str] = mapped_column(String(50), nullable=False) # daily, quest, transfer
    description: Mapped[str] = mapped_column(String(255))
    reference_id: Mapped[Optional[str]] = mapped_column(String(100)) # e.g., quest_id
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    
    user: Mapped[User] = relationship("User", back_populates="transactions")


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
    
    # Type and configuration
    type: Mapped[QuestType] = mapped_column(
        SQLEnum(QuestType),
        default=QuestType.STANDARD,
        server_default=QuestType.STANDARD.value,
    )
    time_limit_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True) # For timed quests
    next_quest_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("quests.id"),
        nullable=True
    ) # For tiered quests
    
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
        default=QuestStatus.ACTIVE,
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


class Achievement(Base):
    """Achievement model."""
    
    __tablename__ = "achievements"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text)
    icon: Mapped[str] = mapped_column(String(10), default="🏆")
    requirement: Mapped[int] = mapped_column(Integer, default=1)
    reward: Mapped[int] = mapped_column(Integer, default=50)
    category: Mapped[str] = mapped_column(String(50), default="general")
    
    # Advanced triggers
    trigger_type: Mapped[str] = mapped_column(String(50), default="standard") # streak, rarity, seasonal
    trigger_value: Mapped[str] = mapped_column(String(100), nullable=True) # e.g. "legendary", "winter_2026"
    
    user_achievements: Mapped[list["UserAchievement"]] = relationship(
        "UserAchievement",
        back_populates="achievement",
        cascade="all, delete-orphan",
    )


class UserAchievement(Base):
    """User achievement progress model."""
    
    __tablename__ = "user_achievements"
    
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    achievement_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("achievements.id", ondelete="CASCADE"),
        primary_key=True,
    )
    unlocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    
    user: Mapped[User] = relationship("User", back_populates="user_achievements")
    achievement: Mapped[Achievement] = relationship("Achievement", back_populates="user_achievements")
