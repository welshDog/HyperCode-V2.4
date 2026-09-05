"""Fail-closed structured-verdict client for Safety Shepherd /evaluate.

Same discipline as fleet-controller/safety_client.py: any timeout, non-200,
unparseable body, or body missing `decision` returns the frozen
_FAIL_CLOSED verdict. A well-formed structured verdict passes through with
the new risk_class / policy_version / allowed_actions / blocked_actions
fields. No off/monitor mode — this path is unconditionally enforced.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

import httpx

_FALLBACK_RISK = "INFRASTRUCTURE_MUTATION"


@dataclass(frozen=True)
class Verdict:
    """One Safety Shepherd `/evaluate` result, structured or fail-closed."""

    decision: str
    reason: str
    risk_class: str
    policy_version: str
    allowed_actions: list = field(default_factory=list)
    blocked_actions: list = field(default_factory=list)
    event_id: Optional[str] = None
    shepherd_available: bool = True
    fail_closed: bool = False


_FAIL_CLOSED = Verdict(
    decision="BLOCK",
    reason="Safety Shepherd unavailable; fail-closed",
    risk_class=_FALLBACK_RISK,
    policy_version="unknown",
    shepherd_available=False,
    fail_closed=True,
)

_client: Optional[httpx.AsyncClient] = None


def _url() -> str:
    """Base URL for Safety Shepherd, env-overridable."""
    return (os.getenv("SAFETY_SHEPHERD_URL") or "http://safety-shepherd:8096").rstrip("/")


def _headers() -> dict:
    """Auth header for Shepherd calls, or {} if no API_KEY is set."""
    key = (os.getenv("API_KEY") or "").strip()
    return {"X-Agent-Key": key} if key else {}


def _get_client() -> httpx.AsyncClient:
    """Return the module-wide httpx client, creating it on first use."""
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=3.0)
    return _client


async def aclose() -> None:
    """Close the shared httpx client, if one was ever created."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def healthy() -> bool:
    """True only on a real 200 from Shepherd's /health; any error is unhealthy."""
    try:
        resp = await _get_client().get(f"{_url()}/health")
        return resp.status_code == 200
    except Exception:
        return False


async def evaluate_plan(*, mission_id: str, plan_hash: str, action: str, target: Optional[str]) -> Verdict:
    """Ask Shepherd to evaluate this action; fail-closed on any timeout,
    non-200, unparseable body, or a body missing `decision`.
    """
    body = {
        "agent": "governor",
        "category": "docker",
        "tool": action,
        "target": target,
        "domain": None,
        "context": {"mission_id": mission_id, "plan_hash": plan_hash},
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
    return Verdict(
        decision=str(data["decision"]).upper(),
        reason=str(data.get("reason") or ""),
        risk_class=str(data.get("risk_class") or _FALLBACK_RISK),
        policy_version=str(data.get("policy_version") or "unknown"),
        allowed_actions=list(data.get("allowed_actions") or []),
        blocked_actions=list(data.get("blocked_actions") or []),
        event_id=data.get("event_id"),
        shepherd_available=True,
        fail_closed=False,
    )
