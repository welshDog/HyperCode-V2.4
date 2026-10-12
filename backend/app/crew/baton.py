"""The Baton — the typed handoff between two crew roles.

Design: docs/superpowers/specs/2026-10-02-hypercrew-next-level-design.md §3.1.
Hard length caps keep handoffs short (ADHD-friendly) and keep model context small.
Evidence is referenced by hash, never pasted.
"""

from __future__ import annotations

from typing import Annotated, List, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Role = Literal[
    "conductor", "scout", "architect", "builder", "verifier",
    "guardian", "healer", "focus_guide", "scribe",
]
RiskHint = Literal["read", "propose", "mutation"]
EvidenceKind = Literal["diff", "test", "log"]

MAX_GOAL = 200
MAX_NEXT_ACTION = 200
MAX_LINE = 140
MAX_DONE = 5
MAX_CONSTRAINTS = 8
MAX_QUESTIONS = 5
MAX_EVIDENCE = 10

# One short line: stripped, non-empty, no newlines.
_Line = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_LINE, pattern=r"^[^\r\n]+$")]
_Goal = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_GOAL, pattern=r"^[^\r\n]+$")]
_Action = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_NEXT_ACTION, pattern=r"^[^\r\n]+$")]
_BatonId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_.:-]{1,128}$")]


class Evidence(BaseModel):
    """A pointer to proof. The content lives elsewhere; the sha256 pins it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: EvidenceKind
    ref: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=256, pattern=r"^[^\r\n]+$")]
    sha256: Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class Baton(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    baton_id: _BatonId
    from_role: Role
    to_role: Role
    goal: _Goal
    done_so_far: List[_Line] = Field(default_factory=list, max_length=MAX_DONE)
    next_action: _Action
    constraints: List[_Line] = Field(default_factory=list, max_length=MAX_CONSTRAINTS)
    evidence: List[Evidence] = Field(default_factory=list, max_length=MAX_EVIDENCE)
    open_questions: List[_Line] = Field(default_factory=list, max_length=MAX_QUESTIONS)
    risk_hint: RiskHint = "read"

    @model_validator(mode="after")
    def _handoff_goes_somewhere(self) -> "Baton":
        if self.from_role == self.to_role:
            raise ValueError("a baton must pass between two different roles")
        return self

    @property
    def is_mutating(self) -> bool:
        return self.risk_hint == "mutation"
