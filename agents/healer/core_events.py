"""
Phase 10E — healer's own identity for agent->core calls.

Publishes heal events to core's POST /api/v1/events authenticated as
healer-agent via X-Agent-Key (registered in the agent_api_keys table).
Fail-open everywhere: a missing key or unreachable core must never
affect healing.
"""
from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger("healer.core_events")


def _self_agent_key() -> str:
    """Env first, then the registered Docker secret. Empty = mirroring off."""
    key = (os.getenv("HYPERCODE_AGENT_KEY") or "").strip()
    if key:
        return key
    path = os.getenv(
        "HYPERCODE_AGENT_KEY_FILE", "/run/secrets/agent_api_key_healer-agent"
    )
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


async def publish_core_event(event_status: str, task_id: str, payload: dict) -> None:
    """Mirror a heal event to core's event stream on channel "ops"."""
    key = _self_agent_key()
    if not key:
        return
    core_url = os.getenv("CORE_URL", "http://hypercode-core:8000").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{core_url}/api/v1/events",
                headers={"X-Agent-Key": key},
                json={
                    "channel": "ops",
                    "agentId": "healer-agent",
                    "taskId": task_id,
                    "status": event_status,
                    "payload": payload,
                },
            )
    except Exception as exc:
        logger.warning("core event publish failed (non-fatal): %s", exc)
