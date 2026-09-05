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


def _read_secret_file(path: str) -> str:
    """Read a secret file's contents, or "" if missing/unreadable/undecodable."""
    # utf-8-sig strips a Windows-editor BOM at read time instead of letting
    # it become part of the compared/sent value; UnicodeDecodeError is
    # caught alongside OSError so a non-UTF-8 secret file fails closed
    # (empty string, same as a missing file) instead of crashing init().
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return f.read().strip()
    except (OSError, UnicodeDecodeError):
        return ""


def _core_agent_key() -> str:
    """Key governor presents to core (X-Agent-Key). env-or-file, mirroring
    safety_shepherd.py's _core_agent_key() exactly: CORE_AGENT_KEY_FILE
    (the Docker-secret path docker-compose.secrets.yml actually sets for
    governor) takes precedence, falling back to the plain CORE_AGENT_KEY
    env var. Without this, init() always read a var nothing ever sets in
    the deployed configuration and permanently no-op'd every ledger write."""
    file_path = os.getenv("CORE_AGENT_KEY_FILE", "")
    if file_path:
        from_file = _read_secret_file(file_path)
        if from_file:
            return from_file
    return (os.getenv("CORE_AGENT_KEY") or "").strip()


def init() -> None:
    """Create the ledger HTTP client, or leave it None (permanent no-op)
    if no CORE_AGENT_KEY is configured.
    """
    global _client
    key = _core_agent_key()
    if not key:
        return
    core_url = (os.getenv("CORE_URL") or "http://hypercode-core:8000").rstrip("/")
    _client = httpx.AsyncClient(base_url=core_url, timeout=3.0, headers={"X-Agent-Key": key})


async def aclose() -> None:
    """Cancel any in-flight ledger writes and close the HTTP client."""
    global _client
    for task in list(_tasks):
        task.cancel()
    if _client is not None:
        await _client.aclose()
        _client = None


def build_body(action: str, decision: str, payload: dict) -> dict:
    """Shape one ledger row's JSON body."""
    return {
        "agent": "governor",
        "action": action,
        "decision": decision,
        "user_id": "system",
        "payload": payload,
    }


async def _write(action: str, decision: str, payload: dict) -> None:
    """POST one ledger row; swallows every exception (fire-and-forget)."""
    client = _client
    if client is None:
        return
    try:
        await client.post(LEDGER_PATH, json=build_body(action, decision, payload))
    except Exception:
        pass


def record(action: str, decision: str, payload: dict) -> None:
    """Fire off a ledger write without blocking the caller. No-op if the
    client was never initialized (no CORE_AGENT_KEY). Never raises, and
    doesn't guarantee the write actually lands — see the module docstring.
    """
    if _client is None:
        return
    task = asyncio.create_task(_write(action, decision, payload))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
