"""
Fail-closed Safety Shepherd client for infrastructure-mutation-class checks.

Deliberately NOT crew-orchestrator's agents/crew-orchestrator/safety_gate.py
pattern: that module fails OPEN on any Shepherd error ("a dead sidecar must
not stop the crew") — correct for its use case, routine task dispatch with
3 existing live callers. This module exists for a different use case where
that tradeoff is wrong: a component whose entire job is proving a
containment boundary must never treat "I couldn't check" as "it's fine."

There is no off/monitor/enforce mode here, unlike safety_gate.py — this
path is unconditionally enforced. Every failure branch returns the same
frozen _FAIL_CLOSED constant, so there is exactly one object identity to
assert against in tests.

Calls Safety Shepherd's existing, UNMODIFIED /evaluate endpoint with
category="docker" — already in Shepherd's DANGEROUS set (policy.py), so it
already defaults to ESCALATE without an explicit capability grant. No
Shepherd-side changes needed for Phase 0.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import httpx

from models import PlanRequest


@dataclass(frozen=True)
class SafetyResult:
    decision: str  # ALLOW | BLOCK | ESCALATE
    reason: str
    rule: Optional[str] = None
    category: Optional[str] = None
    shepherd_available: bool = True
    fail_closed: bool = False


_FAIL_CLOSED = SafetyResult(
    decision="BLOCK",
    reason="Safety Shepherd unavailable; fail-closed",
    shepherd_available=False,
    fail_closed=True,
)

_client: Optional[httpx.AsyncClient] = None


def _url() -> str:
    return (os.getenv("SAFETY_SHEPHERD_URL") or "http://safety-shepherd:8096").rstrip("/")


def _headers() -> dict[str, str]:
    key = (os.getenv("API_KEY") or "").strip()
    return {"X-Agent-Key": key} if key else {}


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=3.0)
    return _client


async def aclose() -> None:
    """Close the shared client (call from the app lifespan shutdown)."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def check_infrastructure_mutation(plan: PlanRequest, plan_hash: str) -> SafetyResult:
    body = {
        "agent": "fleet-controller",
        "category": "docker",
        "tool": None,
        "target": None,
        "domain": None,
        "context": {"mission_id": plan.mission_id, "plan_hash": plan_hash},
    }
    try:
        resp = await _get_client().post(f"{_url()}/evaluate", json=body, headers=_headers())
    except Exception:
        return _FAIL_CLOSED

    if resp.status_code != 200:
        return _FAIL_CLOSED

    try:
        data = resp.json()
    except Exception:
        return _FAIL_CLOSED

    if not isinstance(data, dict) or "decision" not in data:
        return _FAIL_CLOSED

    return SafetyResult(
        decision=str(data["decision"]).upper(),
        reason=str(data.get("reason") or ""),
        rule=data.get("rule"),
        category=data.get("category"),
        shepherd_available=True,
        fail_closed=False,
    )
