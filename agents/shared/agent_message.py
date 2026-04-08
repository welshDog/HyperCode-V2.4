"""
HyperCode V2.0 — Universal Agent Message Schema
================================================
Every agent MUST use this contract to communicate.
Plugs into Redis pub/sub on channel: hypercode:agent:events

Usage:
    from agents.shared.agent_message import AgentMessage, HealEvent

    msg = AgentMessage(
        agent_id="healer-01",
        agent_type="healer",
        status="success",
        xp_earned=50,
    )
    await bus.publish(msg)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ── Status types ──────────────────────────────────────────────────────────────
AgentStatus = Literal[
    "started",
    "running",
    "success",
    "failed",
    "healing",
    "healing_success",
    "throttled",
    "idle",
]

ErrorCategory = Literal[
    "network",
    "llm_timeout",
    "db_connection",
    "auth",
    "logic",
    "unknown",
]


# ── Core message contract ──────────────────────────────────────────────────────
class AgentMessage(BaseModel):
    """Universal event message — all agents publish this to Redis."""

    message_id: UUID = Field(default_factory=uuid4)
    agent_id: str = Field(..., description="Unique agent identifier e.g. 'healer-01'")
    agent_type: str = Field(..., description="Agent class e.g. 'healer', 'coder', 'architect'")
    task_id: UUID = Field(default_factory=uuid4)
    status: AgentStatus
    payload: dict[str, Any] = Field(default_factory=dict)
    error_trace: str | None = None
    error_category: ErrorCategory | None = None
    xp_earned: int = Field(default=0, ge=0, description="BROski XP for this action")
    broski_coins: float = Field(default=0.0, ge=0.0, description="BROski$ earned")
    duration_ms: int | None = Field(None, description="Task duration in milliseconds")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    session_id: str | None = None

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat(), UUID: str}}

    def to_redis_payload(self) -> str:
        """Serialise to JSON string for Redis pub/sub."""
        return self.model_dump_json()

    @classmethod
    def from_redis_payload(cls, raw: str) -> "AgentMessage":
        """Deserialise from Redis pub/sub."""
        return cls.model_validate_json(raw)

    def is_failure(self) -> bool:
        return self.status == "failed"

    def is_success(self) -> bool:
        return self.status in ("success", "healing_success")

    def summary(self) -> str:
        """Human-readable one-liner for logs."""
        return (
            f"[{self.agent_type}:{self.agent_id}] "
            f"{self.status.upper()} | "
            f"XP+{self.xp_earned} | "
            f"BROski${self.broski_coins:.1f} | "
            f"{self.timestamp.strftime('%H:%M:%S')}"
        )


# ── Specialised subtypes ───────────────────────────────────────────────────────
class HealEvent(AgentMessage):
    """Published by the Healer Agent after a recovery action."""

    agent_type: str = "healer"
    healed_agent_id: str = Field(..., description="Which agent was healed")
    heal_pattern: str = Field(..., description="Pattern type e.g. 'db_reconnect', 'oom_restart'")
    recurrence_count: int = Field(default=1, description="Times this pattern has repeated")
    auto_resolved: bool = Field(default=True, description="Was this resolved without human input?")
    xp_earned: int = 50  # Base XP for a successful heal
    broski_coins: float = 10.0


class RefactorEvent(AgentMessage):
    """Published when autonomous code refactoring occurs."""

    agent_type: str = "coder"
    files_changed: list[str] = Field(default_factory=list)
    lines_added: int = 0
    lines_removed: int = 0
    coverage_before: float | None = None
    coverage_after: float | None = None
    commit_sha: str | None = None
    pr_url: str | None = None
    xp_earned: int = 200  # XP for an auto-refactor commit
    broski_coins: float = 50.0


class ThrottleEvent(AgentMessage):
    """Published by throttle-agent when rate limits are hit."""

    agent_type: str = "throttle"
    provider: str = Field(..., description="e.g. 'openai', 'anthropic', 'ollama'")
    retry_after_seconds: int = 60
    requests_blocked: int = 0
    xp_earned: int = 5  # Small XP for catching a throttle


class ArchitectEvent(AgentMessage):
    """Published by Agent X when a new agent is spawned or upgraded."""

    agent_type: str = "architect"
    spawned_agent_id: str | None = None
    upgraded_agent_id: str | None = None
    agent_level_before: int | None = None
    agent_level_after: int | None = None
    xp_earned: int = 500  # Big XP for spawning/upgrading agents
    broski_coins: float = 100.0


# ── Redis channel constants ────────────────────────────────────────────────────
REDIS_CHANNEL_ALL_EVENTS = "hypercode:agent:events"
REDIS_CHANNEL_HEALER     = "hypercode:agent:healer"
REDIS_CHANNEL_REFACTOR   = "hypercode:agent:refactor"
REDIS_CHANNEL_THROTTLE   = "hypercode:agent:throttle"
REDIS_CHANNEL_ARCHITECT  = "hypercode:agent:architect"
REDIS_CHANNEL_XP         = "hypercode:agent:xp"
REDIS_KEY_EVENT_LOG      = "hypercode:event_log"

# ── XP thresholds for agent levelling ─────────────────────────────────────────
AGENT_XP_LEVELS = {
    1:  0,
    2:  500,
    3:  1_500,
    4:  3_500,
    5:  7_500,   # Level 5+ unlocks expanded autonomy
    6:  15_000,
    7:  30_000,
    8:  60_000,
    9:  100_000,
    10: 200_000, # Max level — full autonomous evolution
}


def xp_to_level(xp: int) -> int:
    """Convert raw XP total to agent level (1-10)."""
    level = 1
    for lvl, threshold in AGENT_XP_LEVELS.items():
        if xp >= threshold:
            level = lvl
    return level
