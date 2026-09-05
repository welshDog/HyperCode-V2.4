"""
Fire-and-forget Governance Ledger write, mirroring
agents/safety-shepherd/safety_shepherd.py's _push_ledger/_spawn_ledger_push
pattern exactly: never awaited from the request path, never raises, never
affects safety.decision or execution.performed. A slow or down
hypercode-core must not add latency or a failure mode to the one response
path that's supposed to be the fail-closed one.

Silently disabled (no-op) if CORE_AGENT_KEY isn't configured — expected in
dev until scripts/seed_agent_api_keys.py has provisioned a real key for
this agent.
"""
from __future__ import annotations

import asyncio
import os
from typing import Optional

import httpx

from models import CapabilityView, PlanRequest
from safety_client import SafetyResult

LEDGER_PATH = "/api/v1/governance/ledger"

_client: Optional[httpx.AsyncClient] = None
_tasks: set[asyncio.Task] = set()


def init() -> None:
    """Create the ledger client if CORE_AGENT_KEY is configured. Call from lifespan startup."""
    global _client
    key = (os.getenv("CORE_AGENT_KEY") or "").strip()
    if not key:
        return
    core_url = (os.getenv("CORE_URL") or "http://hypercode-core:8000").rstrip("/")
    _client = httpx.AsyncClient(base_url=core_url, timeout=3.0, headers={"X-Agent-Key": key})


async def aclose() -> None:
    """Cancel in-flight pushes and close the client. Call from lifespan shutdown."""
    global _client
    for task in list(_tasks):
        task.cancel()
    if _client is not None:
        await _client.aclose()
        _client = None


async def _write(
    plan: PlanRequest,
    plan_id: str,
    plan_hash: str,
    result: SafetyResult,
    capability_view: Optional[CapabilityView],
) -> None:
    """POST one preview ledger row; swallows every exception (fail-soft)."""
    client = _client
    if client is None:
        return
    body = {
        "agent": "fleet-controller",
        "action": "plan.preview",
        "decision": result.decision,
        "user_id": "system",
        "payload": {
            "mission_id": plan.mission_id,
            "plan_id": plan_id,
            "plan_hash": plan_hash,
            "requested_actions": [a.model_dump() for a in plan.requested_actions],
            "safety_reason": result.reason,
            "performed": False,
            # Phase 2: so the capability decision is reconstructable from the
            # ledger alone, not just the (possibly-unlogged) API response.
            "capability_check": (
                capability_view.model_dump() if capability_view is not None else None
            ),
        },
    }
    try:
        await client.post(LEDGER_PATH, json=body)
    except Exception:
        pass  # fail-soft by design


def record_preview(
    plan: PlanRequest,
    plan_id: str,
    plan_hash: str,
    result: SafetyResult,
    capability_view: Optional[CapabilityView] = None,
) -> None:
    """Fire-and-forget. Never call `await` on this — that would defeat the point."""
    if _client is None:
        return
    task = asyncio.create_task(_write(plan, plan_id, plan_hash, result, capability_view))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
