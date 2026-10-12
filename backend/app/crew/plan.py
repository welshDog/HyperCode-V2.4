"""The crew plan a human approves at the plan gate (HyperCrew Day 2).

Deterministic and LLM-free on purpose: the plan is the goal bound to the fixed crew stages,
constraints and limits. The approver sees exactly this, and ``plan_hash`` pins it — the same
hash must come back to approve (see operator API). LLM chunking arrives on a later day.

Why not mission-director: it plans *fleet* changes (compose profiles / crew workflow previews),
not code work, so it is the wrong planner for a build goal.
"""

from __future__ import annotations

import re
from typing import Any, get_args

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.broski_operator.recover import plan_hash as _plan_hash
from app.broski_operator.recover import scrub_text
from app.crew.baton import Role

MAX_GOAL = 500
MIN_GOAL = 3

PLAN_KIND = "crew.plan"
PLAN_VERSION = 1

# Stage order is the flow order. `role` is a Baton role; `gate` stages need a human.
STAGES: tuple[dict[str, str], ...] = (
    {"id": "chunk", "role": "focus_guide", "does": "split the goal into small chunks"},
    {"id": "build", "role": "builder", "does": "write the change on a branch"},
    {"id": "verify", "role": "verifier", "does": "run lint and tests"},
    {"id": "guard", "role": "guardian", "does": "safety check every step"},
    {"id": "review", "role": "human", "does": "you review the diff and evidence"},
    {"id": "seal", "role": "conductor", "does": "seal the evidence bundle"},
)

# Fixed, non-negotiable in this phase. Part of the hash, so an approver sees them.
CONSTRAINTS: tuple[str, ...] = (
    "no container mutation",
    "draft pull request only",
    "human approval before any build step",
)
LIMITS: dict[str, int] = {"max_awake_agents": 3, "max_verify_retries": 2}

_CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")
_SPACE = re.compile(r"\s+")


class CrewStartArgs(BaseModel):
    """Arguments for ``hypercode.crew``. Secrets pasted into a goal are masked before storage."""

    model_config = ConfigDict(extra="forbid")

    goal: str = Field(min_length=MIN_GOAL, max_length=4 * MAX_GOAL)

    @field_validator("goal", mode="after")
    @classmethod
    def _clean_goal(cls, v: str) -> str:
        if _CONTROL.search(v):
            raise ValueError("goal contains control characters")
        v = _SPACE.sub(" ", scrub_text(v)).strip()
        if len(v) < MIN_GOAL:
            raise ValueError(f"goal must be at least {MIN_GOAL} characters")
        if len(v) > MAX_GOAL:
            raise ValueError(f"goal must be at most {MAX_GOAL} characters")
        return v


def build_crew_plan(goal: str, run_id: str) -> dict[str, Any]:
    """The plan document. Pure: same inputs, same output, same hash."""
    return {
        "kind": PLAN_KIND,
        "version": PLAN_VERSION,
        "run_id": run_id,
        "goal": goal,
        "stages": [dict(s) for s in STAGES],
        "constraints": list(CONSTRAINTS),
        "limits": dict(LIMITS),
        "risk_hint": "propose",
    }


def crew_plan_hash(plan: dict[str, Any]) -> str:
    return _plan_hash(plan)


def stage_roles() -> set[str]:
    """Roles the plan hands work to (excluding the human gate)."""
    return {s["role"] for s in STAGES if s["role"] != "human"}


def valid_baton_roles() -> set[str]:
    return set(get_args(Role))
