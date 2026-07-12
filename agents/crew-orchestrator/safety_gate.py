"""Safety Shepherd gate for downstream agent dispatch (P0-2 remaining intercept).

Mirrors the hyperflow_runner contract: SAFETY_SHEPHERD_MODE off|monitor|enforce
(default monitor). monitor records the verdict but always proceeds; enforce
returns BLOCK to the caller and waits on the Shepherd-raised approval for
ESCALATE; an unreachable Shepherd fails open (dispatch is the orchestrator's
day job — a dead sidecar must not stop the crew).

One module-level httpx.AsyncClient for the process lifetime — a per-call
client costs ~280 ms in pool/TLS setup on every dispatch.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

ALLOW = "ALLOW"
BLOCK = "BLOCK"
ESCALATE = "ESCALATE"

_client: Optional[httpx.AsyncClient] = None


def _mode() -> str:
    return (os.getenv("SAFETY_SHEPHERD_MODE") or "monitor").strip().lower()


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


def _skipped(mode: str) -> dict[str, Any]:
    return {"decision": ALLOW, "mode": mode, "skipped": True}


async def evaluate_dispatch(
    agent: str,
    tool: Optional[str],
    task_id: str,
    description: str = "",
) -> dict[str, Any]:
    """Ask the Shepherd about one downstream agent dispatch.

    Returns the Shepherd verdict dict plus ``mode`` and ``skipped``. Fail-open:
    off mode, HTTP errors, and unreachable Shepherd all come back as a skipped
    ALLOW so dispatch proceeds (the skip is logged for the audit trail).
    """
    mode = _mode()
    if mode == "off":
        return _skipped(mode)
    body = {
        "agent": agent,
        "category": "generic",
        "tool": tool,
        "target": None,
        "domain": None,
        "context": {
            "source": "crew-orchestrator",
            "task_id": task_id,
            "description": (description or "")[:200],
        },
    }
    try:
        resp = await _get_client().post(f"{_url()}/evaluate", json=body, headers=_headers())
        if resp.status_code != 200:
            logger.warning(
                json.dumps(
                    {"event": "safety_evaluate_failed", "status": resp.status_code, "task_id": task_id}
                )
            )
            return _skipped(mode)
        data = resp.json()
        if not isinstance(data, dict) or "decision" not in data:
            return _skipped(mode)
        data["decision"] = str(data["decision"]).upper()
        data["mode"] = mode
        data["skipped"] = False
        return data
    except Exception:
        logger.info(json.dumps({"event": "safety_shepherd_unreachable", "task_id": task_id}))
        return _skipped(mode)


def is_enforced(verdict: dict[str, Any]) -> bool:
    """True when the verdict must change control flow (enforce mode, real answer)."""
    return verdict.get("mode") == "enforce" and not verdict.get("skipped")


async def wait_for_shepherd_approval(
    redis_client: Any,
    approval_id: Optional[str],
    timeout: Optional[int] = None,
) -> bool:
    """Wait for a human to resolve the Shepherd-raised ESCALATE approval.

    The Shepherd already published the request on ``approval_requests`` (the
    dashboard streams it); we only poll ``approval:{id}:response`` — same
    contract as hyperflow_runner. No approval_id or timeout ⇒ denied.
    """
    if not approval_id or redis_client is None:
        return False
    deadline = time.time() + (timeout or int(os.getenv("SAFETY_APPROVAL_TIMEOUT", "300")))
    try:
        while time.time() < deadline:
            raw = await redis_client.get(f"approval:{approval_id}:response")
            if raw:
                return str(json.loads(raw).get("status")) == "approved"
            await asyncio.sleep(2)
    except Exception:
        logger.warning(
            json.dumps({"event": "safety_approval_wait_failed", "approval_id": approval_id})
        )
    return False
