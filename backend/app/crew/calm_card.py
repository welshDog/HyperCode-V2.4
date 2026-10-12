"""The Calm Card — what a person sees. Always one next action, never a wall of text.

Rules (spec §6): ≤5 TL;DR lines, exactly one next action, details collapsed by default,
a plain-text rendering with no markdown, and a status that is never "unknown".
"""

from __future__ import annotations

import re
from typing import Annotated, List, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, computed_field, field_validator

from app.crew.baton import Baton

CardStatus = Literal["running", "waiting_on_you", "paused", "blocked", "done"]

MAX_TLDR_LINES = 5
MAX_LINE = 120
MAX_DETAILS = 20

_Line = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_LINE, pattern=r"^[^\r\n]+$")]
_Detail = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]

_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_LIST_MARKER = re.compile(r"^\s*(?:[-*+•]|\d+[.)])\s+")
_MD_CHARS = re.compile(r"[*_`#>~|]+")
_NUMBERED_OR_BULLET = re.compile(r"^\s*(?:[-*+•]|\d+[.)])\s+")


def strip_markdown(text: str) -> str:
    """Plain, TTS-friendly text: links keep their label, markup characters go."""
    out = []
    for line in text.splitlines():
        line = _LINK.sub(r"\1", line)
        line = _LIST_MARKER.sub("", line)
        line = _MD_CHARS.sub("", line)
        out.append(re.sub(r"[ \t]+", " ", line).strip())
    return "\n".join(line for line in out if line)


class CalmCard(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: CardStatus
    tldr: List[_Line] = Field(min_length=1, max_length=MAX_TLDR_LINES)
    next_action: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_LINE, pattern=r"^[^\r\n]+$")]
    details: List[_Detail] = Field(default_factory=list, max_length=MAX_DETAILS)
    details_collapsed: bool = True

    @field_validator("next_action")
    @classmethod
    def _exactly_one_action(cls, v: str) -> str:
        if _NUMBERED_OR_BULLET.match(v):
            raise ValueError("next_action must be one action, not a list item")
        return v

    @computed_field  # type: ignore[prop-decorator]
    @property
    def plain_text(self) -> str:
        """Markdown-free rendering: summary, one next step, nothing else."""
        lines = [strip_markdown(t) for t in self.tldr]
        lines.append(f"Next: {strip_markdown(self.next_action)}")
        return "\n".join(line for line in lines if line)

    @classmethod
    def from_baton(cls, baton: Baton, status: CardStatus = "running") -> "CalmCard":
        """Card for a handoff: last ≤5 things done, the baton's one next action."""
        done = baton.done_so_far[-MAX_TLDR_LINES:] or [baton.goal[:MAX_LINE]]
        details = [f"Open question: {q}" for q in baton.open_questions]
        details += [f"Constraint: {c}" for c in baton.constraints]
        return cls(
            status=status,
            tldr=[d[:MAX_LINE] for d in done],
            next_action=baton.next_action[:MAX_LINE],
            details=details,
        )
