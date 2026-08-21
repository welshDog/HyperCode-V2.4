# agents/mission-director/ledger_client.py
"""
Fire-and-forget Governance Ledger write, mirroring
agents/fleet-controller/ledger_client.py exactly: never awaited from the
request path, never raises, never affects status or execution.performed.
A slow or down hypercode-core must not add latency or a failure mode to
mission-director's response path.

Silently disabled (no-op) if CORE_AGENT_KEY isn't configured -- expected
until this agent's scoped key is provisioned (Task 5).
"""
from __future__ import annotations

import asyncio
import os
from typing import Optional

import httpx

from models import MissionProposal

LEDGER_PATH = "/api/v1/governance/ledger"

_client: Optional[httpx.AsyncClient] = None
_tasks: set[asyncio.Task] = set()


def init() -> None:
    global _client
    key = (os.getenv("CORE_AGENT_KEY") or "").strip()
    if not key:
        return
    core_url = (os.getenv("CORE_URL") or "http://hypercode-core:8000").rstrip("/")
    _client = httpx.AsyncClient(base_url=core_url, timeout=3.0, headers={"X-Agent-Key": key})


async def aclose() -> None:
    global _client
    for task in list(_tasks):
        task.cancel()
    if _client is not None:
        await _client.aclose()
        _client = None


async def _write(proposal: MissionProposal) -> None:
    client = _client
    if client is None:
        return
    body = {
        "agent": "mission-director",
        "action": "mission.propose",
        "decision": proposal.status,
        "user_id": "system",
        "payload": proposal.model_dump(mode="json"),
    }
    try:
        await client.post(LEDGER_PATH, json=body)
    except Exception:
        pass  # fail-soft by design


def record_proposal(proposal: MissionProposal) -> None:
    """Fire-and-forget. Never call `await` on this."""
    if _client is None:
        return
    task = asyncio.create_task(_write(proposal))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
