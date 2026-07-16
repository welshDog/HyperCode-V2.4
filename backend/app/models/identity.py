"""BROskiIdentityAgent model — a resident agent object per user (P1-1).

One row per user. ``state`` (JSONB) holds the user's resident agent state —
course progress, tier, pet IDs, permissions, and a capped recent-actions log.
Schema created by migration 017_add_broski_identity_agents.

Note: the AGENT-START brief said "FK -> broski_wallets.discord_id", but that
column does not exist (discord_id lives on users; broski_wallets keys on
users.id). We FK to users.id — the real canonical key, consistent with
broski_wallets — and denormalise discord_id for convenience.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base_class import Base


class BROskiIdentityAgent(Base):
    __tablename__ = "broski_identity_agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True
    )
    discord_id: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    # { tier, course_progress, pet_ids, permissions, recent_actions: [...] }
    state: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(SQLiteJSON(), "sqlite"), nullable=False, default=dict
    )
    last_active: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
