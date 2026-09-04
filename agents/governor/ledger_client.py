"""Fire-and-forget Governance Ledger write. Mirrors fleet-controller's
ledger_client: never awaited from a request path, never raises, no-op
until CORE_AGENT_KEY is provisioned."""
from __future__ import annotations

import asyncio
import os
from typing import Optional

import httpx

LEDGER_PATH = "/api/v1/governance/ledger"

_client: Optional[httpx.AsyncClient] = None
_tasks: set = set()


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


def build_body(action: str, decision: str, payload: dict) -> dict:
    return {
        "agent": "governor",
        "action": action,
        "decision": decision,
        "user_id": "system",
        "payload": payload,
    }


async def _write(action: str, decision: str, payload: dict) -> None:
    client = _client
    if client is None:
        return
    try:
        await client.post(LEDGER_PATH, json=build_body(action, decision, payload))
    except Exception:
        pass


def record(action: str, decision: str, payload: dict) -> None:
    if _client is None:
        return
    task = asyncio.create_task(_write(action, decision, payload))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
