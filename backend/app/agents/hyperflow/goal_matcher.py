"""Deterministic free-text goal → existing-flow matcher.

Token-overlap (Jaccard) scoring only — never invents new flow topology.
A goal either confidently matches one existing, already-reviewed flow, or
it doesn't match at all. See docs/superpowers/specs/2026-08-15-hyperflow-goal-matcher-design.md.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from app.agents.hyperflow.schema import FlowDefinition

_TOKEN_RE = re.compile(r"[a-z0-9]+")
DEFAULT_THRESHOLD = 0.4


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    union = len(a | b)
    return len(a & b) / union if union else 0.0


def _match_threshold() -> float:
    raw = os.getenv("HYPERFLOW_MATCH_THRESHOLD", str(DEFAULT_THRESHOLD))
    try:
        return float(raw)
    except ValueError:
        return DEFAULT_THRESHOLD


@dataclass
class CandidateMatch:
    flow: str
    score: float
    intent: str


@dataclass
class MatchResult:
    flow_name: str | None
    score: float
    candidates: list[CandidateMatch] = field(default_factory=list)


def match_goal(description: str, flows: dict[str, FlowDefinition]) -> MatchResult:
    """Match a free-text goal to the best existing flow.

    Returns flow_name=None when nothing clears HYPERFLOW_MATCH_THRESHOLD
    (default 0.4), or when the top two candidates are exactly tied —
    a tie is ambiguous and must never be silently broken by execution.
    Candidates are always sorted score desc, then flow name asc.
    """
    goal_tokens = _tokenize(description)

    candidates = [
        CandidateMatch(
            flow=name,
            score=_jaccard(goal_tokens, _tokenize(f"{fd.name} {fd.intent}")),
            intent=fd.intent,
        )
        for name, fd in flows.items()
    ]
    candidates.sort(key=lambda c: (-c.score, c.flow))

    if not candidates:
        return MatchResult(flow_name=None, score=0.0, candidates=candidates)

    threshold = _match_threshold()
    if candidates[0].score < threshold:
        return MatchResult(flow_name=None, score=0.0, candidates=candidates)

    if len(candidates) > 1 and candidates[0].score == candidates[1].score:
        return MatchResult(flow_name=None, score=candidates[0].score, candidates=candidates)

    top = candidates[0]
    return MatchResult(flow_name=top.flow, score=top.score, candidates=candidates)
