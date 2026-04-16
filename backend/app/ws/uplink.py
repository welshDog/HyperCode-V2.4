"""
Phase 10J — CognitiveUplink WebSocket Handler
HyperCode V2.4 | BROski♾

Endpoint: WS /ws/uplink
Mounted directly on the FastAPI app (not via api_router) so the path is
exactly /ws/uplink — matching CognitiveUplink.tsx.

Message contract (from CognitiveUplink.tsx):
  Inbound:  { type: 'execute', id, payload: { command: str }, ... }
            { type: 'ping', ... }
  Outbound: { type: 'response', payload: str }   → shows as agent message
            { type: 'result',   payload: str }   → alias, same UI slot
            { type: 'error',    data: str }       → toast + system message
            { type: 'pong' }                      → ping reply
"""
from __future__ import annotations

import json
import logging
import os
from uuid import uuid4

import httpx
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.circuit_breaker import get_breaker

_crew_breaker = get_breaker("crew-orchestrator", fail_max=3, reset_timeout=15)

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Config ────────────────────────────────────────────────────────────────────
_CREW_URL       = os.getenv("CREW_ORCHESTRATOR_URL", "http://crew-orchestrator:8080")
_ORCH_API_KEY   = os.getenv("ORCHESTRATOR_API_KEY", "")
_TIMEOUT        = 60.0   # seconds — crew can take a while with RAG + agents


# ── Helpers ───────────────────────────────────────────────────────────────────

def _format_crew_result(command: str, result: dict) -> str:
    """Turn crew-orchestrator's /execute response into a chat-friendly string."""
    status = result.get("status", "unknown")

    if status == "error":
        return f"⚠️ Orchestrator error: {result.get('message', 'unknown error')}"

    if status in ("rejected", "timeout"):
        return f"🛑 Task {status} by approval gate."

    results: dict = result.get("results") or {}
    if results:
        lines = []
        for agent_name, agent_result in results.items():
            output = (
                agent_result.get("output")
                or agent_result.get("message")
                or agent_result.get("result")
                or str(agent_result)
            )
            lines.append(f"**[{agent_name}]**\n{output}")
        return "\n\n".join(lines)

    # No agents ran (no agent specified) — friendly ack
    short_cmd = command[:80] + ("…" if len(command) > 80 else "")
    return (
        f"✅ Command dispatched to orchestrator.\n"
        f"Task ID: `{result.get('task_id', 'n/a')}`\n"
        f"> {short_cmd}\n\n"
        f"Tip: specify an agent (e.g. `@backend-specialist build auth`) to route directly."
    )


async def _dispatch_to_crew(command: str, task_id: str) -> dict:
    """POST to crew-orchestrator /execute. Returns the JSON response dict."""
    async def _call() -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{_CREW_URL}/execute",
                json={
                    "id":                task_id,
                    "description":       command,
                    "type":              "user_command",
                    "requires_approval": False,
                },
                headers={"X-API-Key": _ORCH_API_KEY},
                timeout=_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()
            # Attach task_id so _format_crew_result can surface it
            data.setdefault("task_id", task_id)
            return data

    return await _crew_breaker.call(_call)


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@router.websocket("/ws/uplink")
async def ws_uplink(websocket: WebSocket) -> None:
    """
    CognitiveUplink neural interface.
    Accepts UplinkMessage from the dashboard, dispatches to crew-orchestrator,
    and streams the result back.
    """
    await websocket.accept()
    client_host = websocket.client.host if websocket.client else "unknown"
    logger.info(f"[uplink] connection from {client_host}")

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                msg: dict = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({"type": "error", "data": "Invalid JSON payload"})
                )
                continue

            msg_type = msg.get("type", "")

            # ── Ping / keepalive ──────────────────────────────────────────────
            if msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
                continue

            # ── Execute directive ─────────────────────────────────────────────
            if msg_type == "execute":
                payload = msg.get("payload") or {}
                command: str = (
                    payload.get("command", "")
                    if isinstance(payload, dict)
                    else str(payload)
                ).strip()

                if not command:
                    await websocket.send_text(
                        json.dumps({"type": "error", "data": "Empty command — nothing to dispatch"})
                    )
                    continue

                task_id = msg.get("id") or f"uplink-{uuid4().hex[:8]}"
                logger.info(f"[uplink] execute task_id={task_id} cmd={command[:60]!r}")

                try:
                    result = await _dispatch_to_crew(command, task_id)
                    response_text = _format_crew_result(command, result)
                    await websocket.send_text(
                        json.dumps({"type": "response", "payload": response_text})
                    )

                except httpx.TimeoutException:
                    logger.warning(f"[uplink] crew-orchestrator timeout task_id={task_id}")
                    await websocket.send_text(json.dumps({
                        "type":    "error",
                        "data":    "Orchestrator timed out (>60s). Task may still be running.",
                    }))

                except httpx.HTTPStatusError as exc:
                    logger.error(f"[uplink] crew HTTP {exc.response.status_code} task_id={task_id}")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "data": f"Orchestrator returned {exc.response.status_code}: {exc.response.text[:200]}",
                    }))

                except Exception as exc:
                    logger.exception(f"[uplink] dispatch error task_id={task_id}")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "data": f"Dispatch failed: {exc}",
                    }))

                continue

            # ── Unknown type ──────────────────────────────────────────────────
            logger.debug(f"[uplink] unknown message type={msg_type!r} — ignored")

    except WebSocketDisconnect:
        logger.info(f"[uplink] client {client_host} disconnected")
    except Exception:
        logger.exception("[uplink] unexpected error — closing socket")
