"""Slim request/response models for Phase 1 (observe -> explain).

The Phase 2 mission-envelope models were removed from this agent: proposals must
flow through mission-director -> fleet-controller, not a direct endpoint here.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ResearchBriefRequest(BaseModel):
    """Ad-hoc research brief on a single topic."""

    topic: str = Field(..., min_length=2, description="Topic to research")
    max_sources: int = Field(default=10, ge=1, le=50)
    categories: list[str] | None = Field(
        default=None, description="Override the default arXiv categories"
    )


class Paper(BaseModel):
    arxiv_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    summary: str = ""
    published: str = ""
    url: str = ""
    categories: list[str] = Field(default_factory=list)


class BriefResult(BaseModel):
    """The output of a sweep or an ad-hoc topic brief."""

    kind: str = Field(description="'sweep' or 'topic'")
    topic: str | None = None
    window: str = ""
    categories: list[str] = Field(default_factory=list)
    new_count: int = 0
    papers: list[Paper] = Field(default_factory=list)
    markdown: str = ""
    generated_at: datetime = Field(default_factory=_utcnow)
    generated_by: str = "academic_brain"
    sinks: dict[str, Any] = Field(default_factory=dict, description="Per-sink delivery result")
