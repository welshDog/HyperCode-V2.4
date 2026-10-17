"""
HyperHealth Pydantic models
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, AnyHttpUrl

CheckType = Literal["cpu", "memory", "disk", "network", "http", "db", "queue",
                    "cache", "tls", "vuln_scan", "compliance"]


class ThresholdConfig(BaseModel):
    warn: float
    crit: float


class CheckDefinitionCreate(BaseModel):
    name: str
    type: CheckType
    target: str
    environment: str = "prod"
    interval_seconds: int = 30
    thresholds: ThresholdConfig = ThresholdConfig(warn=1000, crit=5000)
    alert_policy_id: Optional[int] = None
    self_heal_policy_id: Optional[int] = None
    tags: List[str] = []


class CheckDefinitionOut(BaseModel):
    id: UUID
    name: str
    type: str
    target: str
    environment: str
    interval_seconds: int
    enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def model_validate(cls, obj, *args, **kwargs):
        if isinstance(obj, dict):
            data = dict(obj)
        else:
            data = {name: getattr(obj, name) for name in cls.model_fields if hasattr(obj, name)}
        target = str(data.get("target", ""))
        if "://" in target and "@" in target:
            from urllib.parse import urlsplit, urlunsplit
            parsed = urlsplit(target)
            if parsed.username or parsed.password:
                host = parsed.hostname or "redacted"
                if parsed.port:
                    host += f":{parsed.port}"
                data["target"] = urlunsplit((parsed.scheme, host, parsed.path, parsed.query, parsed.fragment))
        return super().model_validate(data, *args, **kwargs)


class CheckResultOut(BaseModel):
    id: UUID
    check_id: UUID
    status: str
    latency_ms: Optional[float]
    value: Optional[str]
    message: Optional[str]
    environment: str
    started_at: datetime

    model_config = {"from_attributes": True}


class IncidentOut(BaseModel):
    id: UUID
    check_id: Optional[UUID]
    title: str
    severity: str
    environment: str
    created_at: datetime
    resolved_at: Optional[datetime]

    model_config = {"from_attributes": True}


class HealthReport(BaseModel):
    environment: str
    overall_status: str
    total_checks: int
    critical_count: int
    warning_count: int
    ok_count: int
    open_incidents: List[Dict[str, Any]]
    generated_at: str


class SelfHealPolicyCreate(BaseModel):
    name: str
    action: str
    enabled: bool = True
    trigger_threshold: int = 3
    cooldown_minutes: int = 5
