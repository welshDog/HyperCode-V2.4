"""HyperFlowRun model — persisted state of a mission-graph run (P0-1).

One row per flow execution. ``state`` holds the full node-transition history as
JSONB so a GET is always current even though the runner walks the graph in an
in-core asyncio task. Schema created by migration 016_add_hyperflow_runs.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base_class import Base


class HyperFlowRunStatus(str, enum.Enum):
    RUNNING            = "running"
    AWAITING_APPROVAL  = "awaiting_approval"
    COMPLETED          = "completed"
    FAILED             = "failed"


class HyperFlowRun(Base):
    __tablename__ = "hyperflow_runs"

    id:           Mapped[str]           = mapped_column(String(36), primary_key=True)
    flow_name:    Mapped[str]           = mapped_column(String(128), nullable=False, index=True)
    flow_version: Mapped[int]           = mapped_column(Integer, nullable=False, default=1)
    status:       Mapped[str]           = mapped_column(
        String(24), nullable=False, server_default=HyperFlowRunStatus.RUNNING.value, index=True
    )
    current_node: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    # { "history": [ {node, type, status, result, ts}, ... ], "context": {...} }
    state:        Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at:   Mapped[datetime]      = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at:   Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
