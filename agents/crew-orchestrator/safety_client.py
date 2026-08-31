"""Fail-closed Safety Shepherd client for agent-dispatch-class checks.

Sits beside ``safety_gate.py`` and is deliberately its opposite. ``safety_gate``
fails OPEN on any Shepherd error — correct for routine task dispatch, where a
dead sidecar must not stop the crew. This module is for the case where that
trade-off is wrong: a dispatch that can reach a mutation-capable executor must
never treat "I couldn't check" as "it's fine."

There is no on/off switch and no observe-only path here — this client is
unconditionally strict. Every failure branch returns the same frozen
``_FAIL_CLOSED`` constant, so tests have exactly one object identity to assert
against.

The request body mirrors ``safety_gate.evaluate_dispatch`` byte-for-byte
(agent, category="generic", tool, target=None, domain=None, context with
source/task_id/truncated description) so the fail-open and fail-closed paths
send the Shepherd identical input. That is what makes the card (b) canary —
comparing the two paths' verdicts before the strict route is switched on —
meaningful.

Not wired into main.py yet; that is card (c).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import httpx

_DISPATCH_SOURCE = "crew-orchestrator"


@dataclass(frozen=True)
class DispatchRequest:
    """One downstream agent dispatch, as a distinct security object.

    Not a deployment plan and not ``dict[str, Any]`` — the strict client only
    ever speaks this shape.
    """

    agent: str
    tool: Optional[str]  # carries the task *type* (mirrors safety_gate.evaluate_dispatch's `tool` arg), not a tool name
    task_id: str
    description: str = ""


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
    key = (os.getenv("HYPERCODE_API_KEY") or os.getenv("API_KEY") or "").strip()
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


async def check_dispatch(dispatch: DispatchRequest) -> SafetyResult:
    """Ask the Shepherd about one downstream agent dispatch, fail-closed.

    Any failure to obtain a well-formed verdict — timeout, connection error,
    non-200, unparseable body, non-dict body, or a body with no ``decision`` —
    returns the ``_FAIL_CLOSED`` singleton. A well-formed verdict passes
    through unchanged (including a real Shepherd ``BLOCK``, which is distinct
    from the fail-closed one).
    """
    body = {
        "agent": dispatch.agent,
        "category": "generic",
        "tool": dispatch.tool,
        "target": None,
        "domain": None,
        "context": {
            "source": _DISPATCH_SOURCE,
            "task_id": dispatch.task_id,
            "description": (dispatch.description or "")[:200],
        },
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
