from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base_class import Base


class PetProvisionEvent(Base):
    __tablename__ = "pet_provision_events"
    __table_args__ = (UniqueConstraint("source_id", name="uq_pet_provision_source_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    discord_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    pet_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
