"""
Task 6 — Logs Broadcaster
Provides:
  GET  /api/v1/logs      — paged log history with optional filters (no auth required)
  WS   /api/v1/ws/logs   — real-time log stream via Redis pub/sub

Redis storage:
  hypercode:logs         — RPUSH list capped to 1000 entries
  hypercode:logs:channel — pub/sub channel for live fanout

Log entry schema (JSON):
  { id, time, agent, level, msg }

Agents/services push logs via RPUSH hypercode:logs + PUBLISH hypercode:logs:channel.
The existing dashboard.py /logs endpoint (JWT-gated) remains untouched.
This module adds a public (no-auth) fast-path for the live dashboard.
"""

import asyncio
import datetime
import json
import logging
import uuid
from typing import List, Optional, Set

import redis.asyncio as aioredis
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

LOGS_LIST_KEY    = "hypercode:logs"
LOGS_CHANNEL_KEY = "hypercode:logs:channel"
MAX_STORED_LOGS  = 1_000


# ── Pydantic models ────────────────────────────────────────────────────────────

class LogEntry(BaseModel):
    id: str
    time: str
    agent: str
    level: str   # "info" | "warn" | "error" | "success"
    msg: str


class LogResponse(BaseModel):
    logs: List[LogEntry]
    total: int


# ── Connection manager ─────────────────────────────────────────────────────────

class ConnectionManager:
    def __init__(self) -> None:
        self._clients: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.add(ws)

    def disconnect(self, ws: WebSocket) -> None:
        self._clients.discard(ws)

    async def broadcast(self, data: str) -> None:
        dead: Set[WebSocket] = set()
        for ws in list(self._clients):
            try:
                await ws.send_text(data)
            except Exception:
                dead.add(ws)
        self._clients -= dead


_manager = ConnectionManager()


# ── REST: GET /api/v1/logs (no auth) ──────────────────────────────────────────

@router.get("/logs", response_model=LogResponse)
async def get_logs(
    limit: int = Query(default=80, ge=1, le=500),
    level: Optional[str] = Query(default=None),
    agent: Optional[str] = Query(default=None),
) -> LogResponse:
    """
    Returns recent log entries from Redis.
    Optionally filter by level (info/warn/error/success) or agent name.
    No authentication required — suitable for the live dashboard panel.
    """
    r = await aioredis.from_url(settings.HYPERCODE_REDIS_URL, decode_responses=True)
    try:
        raw_entries = await r.lrange(LOGS_LIST_KEY, -MAX_STORED_LOGS, -1)
    finally:
        await r.aclose()

    entries: List[LogEntry] = []
    for raw in reversed(raw_entries):  # newest first
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            continue
        entry = LogEntry(
            id=str(data.get("id", uuid.uuid4())),
            time=str(data.get("time", data.get("timestamp", ""))),
            agent=str(data.get("agent", data.get("agentId", "system"))),
            level=str(data.get("level", "info")),
            msg=str(data.get("msg", data.get("message", ""))),
        )
        if level and entry.level != level:
            continue
        if agent and agent.lower() not in entry.agent.lower():
            continue
        entries.append(entry)
        if len(entries) >= limit:
            break

    return LogResponse(logs=entries, total=len(entries))


# ── WebSocket: WS /api/v1/ws/logs ─────────────────────────────────────────────

@router.websocket("/ws/logs")
async def ws_logs(websocket: WebSocket) -> None:
    """
    WebSocket — streams log entries in real time via Redis pub/sub.
    On connect: sends last 20 log entries as `logs:history` channel messages.
    Live: sends new entries as `logs:live` channel messages.
    Clients connect to ws://hypercode-core:8000/api/v1/ws/logs
    """
    await _manager.connect(websocket)
    r = await aioredis.from_url(settings.HYPERCODE_REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()
    try:
        # Seed with history
        history_raw = await r.lrange(LOGS_LIST_KEY, -20, -1)
        for raw in history_raw:
            try:
                data = json.loads(raw)
                await websocket.send_text(
                    json.dumps({"channel": "logs:history", "data": data})
                )
            except Exception:
                pass

        # Live stream
        await pubsub.subscribe(LOGS_CHANNEL_KEY)
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            try:
                data = json.loads(message["data"])
                await websocket.send_text(
                    json.dumps({"channel": "logs:live", "data": data})
                )
            except Exception:
                pass
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("ws_logs connection error")
    finally:
        _manager.disconnect(websocket)
        await pubsub.unsubscribe(LOGS_CHANNEL_KEY)
        await pubsub.close()
        await r.aclose()
