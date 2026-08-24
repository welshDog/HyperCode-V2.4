"""MissionProposal model -- Mission Director Phase 1's own operational
current-state store (point-lookup for the review endpoint's precondition
check). NOT a replacement for the Governance Ledger, which stays the
permanent, append-only audit trail. See
docs/superpowers/specs/2026-08-21-mission-director-phase1-design.md §6.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base_class import Base


class MissionProposal(Base):
    __tablename__ = "mission_proposals"

    mission_id: Mapped[str] = mapped_column(Text, primary_key=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    truth_snapshot_ref: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    plan: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB().with_variant(SQLiteJSON(), "sqlite"), nullable=True
    )
    plan_response: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB().with_variant(SQLiteJSON(), "sqlite"), nullable=True
    )
    impact: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(
        JSONB().with_variant(SQLiteJSON(), "sqlite"), nullable=True
    )
    superseded_from: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
