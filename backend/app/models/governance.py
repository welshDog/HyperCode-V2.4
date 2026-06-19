"""GovernanceLedger model — durable audit trail of high-impact actions (P1-2).

The audit layer ON TOP of the durable economy tables (broski_wallets /
broski_transactions). IdentityAgent.log_action() writes one row here per
high-impact action. Schema created by migration 018_add_governance_ledger.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func, text

from app.db.base_class import Base


class GovernanceLedger(Base):
    __tablename__ = "governance_ledger"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    action: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    tool_used: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    decision: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    agent_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    approved_by: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
