"""MissionEvaluation model -- Mission Evaluator v1's own table. One row
per evaluated mission, written once and never updated (an evaluation is
a point-in-time judgment of a terminal mission, not a live-updating
record). NOT the audit trail (governance_ledger) and NOT
mission_proposals' own current-state store -- a third, narrower table
purpose-built for this observer. See
docs/superpowers/specs/2026-08-21-mission-evaluator-design.md §1.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base_class import Base


class MissionEvaluation(Base):
    __tablename__ = "mission_evaluations"

    mission_id: Mapped[str] = mapped_column(Text, primary_key=True)
    verdict: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    checks: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(SQLiteJSON(), "sqlite"), nullable=False
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
