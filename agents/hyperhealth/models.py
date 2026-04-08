"""
HyperHealth — Data Models
SQLAlchemy ORM tables + Pydantic schemas for all 4 core entities.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, AnyHttpUrl, Field
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, String, Text, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


# ── SQLAlchemy Base ──────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── ORM Models ───────────────────────────────────────────────────────────────
class CheckDefinitionORM(Base):
    __tablename__ = "check_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    type = Column(String(64), nullable=False)
    target = Column(String(512), nullable=False)
    environment = Column(String(64), nullable=False, default="prod")
    interval_seconds = Column(Integer, nullable=False, default=30)
    thresholds = Column(JSON, nullable=False, default=dict)
    alert_policy_id = Column(Integer, ForeignKey("alert_policies.id"), nullable=True)
    self_heal_policy_id = Column(Integer, ForeignKey("self_heal_policies.id"), nullable=True)
    tags = Column(JSON, nullable=False, default=list)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    results = relationship("CheckResultORM", back_populates="check", lazy="dynamic")


class CheckResultORM(Base):
    __tablename__ = "check_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    check_id = Column(UUID(as_uuid=True), ForeignKey("check_definitions.id"), nullable=False)
    status = Column(String(16), nullable=False)  # OK | WARN | CRIT
    latency_ms = Column(Float, nullable=True)
    value = Column(Float, nullable=True)
    message = Column(Text, nullable=True)
    environment = Column(String(64), nullable=False, default="prod")
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

    check = relationship("CheckDefinitionORM", back_populates="results")


class AlertPolicyORM(Base):
    __tablename__ = "alert_policies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    severity_map = Column(JSON, nullable=False, default=dict)
    channels = Column(JSON, nullable=False, default=list)  # ["slack", "email", "pagerduty"]
    dedupe_window_seconds = Column(Integer, nullable=False, default=300)
    escalation_chain = Column(JSON, nullable=False, default=list)
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SelfHealPolicyORM(Base):
    __tablename__ = "self_heal_policies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    trigger_condition = Column(Text, nullable=False)  # "service=X AND status=CRIT AND failures>=3 in 5m"
    action = Column(String(128), nullable=False)   # "restart" | "rollback" | "purge_cache"
    action_params = Column(JSON, nullable=False, default=dict)
    max_retries_per_window = Column(Integer, nullable=False, default=3)
    window_seconds = Column(Integer, nullable=False, default=300)
    enabled = Column(Boolean, nullable=False, default=True)
    require_approval = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Pydantic Schemas ─────────────────────────────────────────────────────────
CheckType = Literal[
    "cpu", "memory", "disk", "network",
    "http", "db", "queue", "cache",
    "tls", "vuln_scan", "compliance"
]

CheckStatus = Literal["OK", "WARN", "CRIT", "UNKNOWN"]


class ThresholdSchema(BaseModel):
    warn: float
    crit: float
    window: int = Field(default=60, description="Window in seconds")


class CheckDefinitionCreate(BaseModel):
    name: str = Field(..., max_length=255)
    type: CheckType
    target: str = Field(..., description="URL, DSN, host:port, queue name, etc.")
    environment: str = Field(default="prod", max_length=64)
    interval_seconds: int = Field(default=30, ge=5, le=86400)
    thresholds: Dict[str, ThresholdSchema] = Field(default_factory=dict)
    alert_policy_id: Optional[int] = None
    self_heal_policy_id: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    enabled: bool = True


class CheckDefinitionOut(BaseModel):
    id: uuid.UUID
    name: str
    type: str
    target: str
    environment: str
    interval_seconds: int
    enabled: bool
    tags: List[str]
    created_at: datetime

    class Config:
        from_attributes = True


class CheckResultOut(BaseModel):
    id: uuid.UUID
    check_id: uuid.UUID
    status: str
    latency_ms: Optional[float]
    value: Optional[float]
    message: Optional[str]
    environment: str
    started_at: datetime
    finished_at: Optional[datetime]

    class Config:
        from_attributes = True


class HealthReportOut(BaseModel):
    environment: str
    generated_at: datetime
    total_checks: int
    status_counts: Dict[str, int]
    overall_status: CheckStatus
    top_incidents: List[Dict[str, Any]]
    self_heals_last_hour: int
    mttr_seconds: Optional[float]
    recommendations: List[str]
