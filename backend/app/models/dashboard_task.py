"""
Task 9 — DashboardTask model
Independent of users/projects — used by the public /api/tasks endpoints.
Schema created by migration 002_dashboard_tasks.
"""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base_class import Base


class DashboardTaskStatus(str, enum.Enum):
    TODO        = "todo"
    IN_PROGRESS = "in_progress"
    DONE        = "done"
    CANCELLED   = "cancelled"


class DashboardTaskSource(str, enum.Enum):
    MANUAL = "manual"
    AUTO   = "auto"    # created by auto-task logic (error rate > 5%)
    SYSTEM = "system"


class DashboardTask(Base):
    __tablename__ = "dashboard_tasks"

    id:          Mapped[int]           = mapped_column(Integer, primary_key=True, index=True)
    title:       Mapped[str]           = mapped_column(String, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status:      Mapped[DashboardTaskStatus] = mapped_column(
        Enum(DashboardTaskStatus), default=DashboardTaskStatus.TODO
    )
    priority:    Mapped[str]           = mapped_column(String, default="medium")
    source:      Mapped[DashboardTaskSource] = mapped_column(
        Enum(DashboardTaskSource), default=DashboardTaskSource.MANUAL
    )
    created_at:  Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:  Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )
