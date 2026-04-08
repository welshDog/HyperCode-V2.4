"""
Task 5 — Events Broadcaster
Provides:
  GET  /api/v1/events       — SSE stream of live system events
  WS   /api/v1/ws/events    — WebSocket stream of live system events
  POST /api/v1/events       — Internal: publish an event (agents/healer call this)

Redis storage:
  hypercode:events          — RPUSH list, capped to 500 entries (LTRIM from the right)
  hypercode:events:channel  — pub/sub channel for real-time fanout to WS clients

Event schema (stored as JSON):
  { id, channel, agentId, taskId, status, payload, timestamp }
"""

import asyncio
import datetime
import json
import logging
import uuid
from typing import Optional, Set

import redis.asyncio as aioredis
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

EVENTS_LIST_KEY    = "hypercode:events"
EVENTS_CHANNEL_KEY = "hypercode:events:channel"
MAX_STORED_EVENTS  = 500


# ── Pydantic models ────────────────────────────────────────────────────────────

class EventPublish(BaseModel):
    channel: str = "system"
    agentId: Optional[str] = None
    taskId: Optional[str] = None
    status: str = "info"
    payload: dict = {}


class AgentEvent(BaseModel):
    id: str
    channel: str
    agentId: str
    taskId: str
    status: str
    payload: dict
    timestamp: str


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


# ── REST: publish event (used internally by agents/healer) ────────────────────

@router.post("/events", response_model=AgentEvent)
async def publish_event(body: EventPublish) -> AgentEvent:
    """Publish a system event to the Redis list and fanout channel."""
    event = AgentEvent(
        id=str(uuid.uuid4()),
        channel=body.channel,
        agentId=body.agentId or "system",
        taskId=body.taskId or "",
        status=body.status,
        payload=body.payload,
        timestamp=datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    payload_json = event.model_dump_json()

    r = await aioredis.from_url(settings.HYPERCODE_REDIS_URL, decode_responses=True)
    try:
        async with r.pipeline(transaction=False) as pipe:
            pipe.rpush(EVENTS_LIST_KEY, payload_json)
            pipe.ltrim(EVENTS_LIST_KEY, -MAX_STORED_EVENTS, -1)
            pipe.publish(EVENTS_CHANNEL_KEY, payload_json)
            await pipe.execute()
    finally:
        await r.aclose()

    return event


# ── SSE: GET /api/v1/events ────────────────────────────────────────────────────

@router.get("/events")
async def sse_events(request: Request):
    """
    Server-Sent Events stream of live system events.
    Sends the last 20 stored events on connect, then streams new ones via Redis pub/sub.
    """
    async def event_generator():
        r = await aioredis.from_url(settings.HYPERCODE_REDIS_URL, decode_responses=True)
        pubsub = r.pubsub()
        try:
            # Seed with history
            history = await r.lrange(EVENTS_LIST_KEY, -20, -1)
            for item in history:
                yield f"data: {item}\n\n"

            # Live stream
            await pubsub.subscribe(EVENTS_CHANNEL_KEY)
            async for message in pubsub.listen():
                if await request.is_disconnected():
                    break
                if message.get("type") != "message":
                    continue
                yield f"data: {message['data']}\n\n"
        except Exception:
            logger.exception("SSE events stream error")
        finally:
            await pubsub.unsubscribe(EVENTS_CHANNEL_KEY)
            await pubsub.close()
            await r.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── WebSocket: WS /api/v1/ws/events ───────────────────────────────────────────

@router.websocket("/ws/events")
async def ws_events(websocket: WebSocket) -> None:
    """
    WebSocket — streams AgentEvent JSON frames in real time via Redis pub/sub.
    Sends last 20 stored events on connect, then live as they arrive.
    Clients connect to ws://hypercode-core:8000/api/v1/ws/events
    """
    await _manager.connect(websocket)
    r = await aioredis.from_url(settings.HYPERCODE_REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()
    try:
        # Seed history
        history = await r.lrange(EVENTS_LIST_KEY, -20, -1)
        for item in history:
            seed_payload = json.loads(item)
            await websocket.send_text(
                json.dumps({"channel": "ws_tasks", "data": seed_payload})
            )

        # Live stream via pub/sub
        await pubsub.subscribe(EVENTS_CHANNEL_KEY)
        async for message in pubsub.listen():
            if message.get("type") != "message":
                continue
            event_data = json.loads(message["data"])
            await websocket.send_text(
                json.dumps({"channel": "ws_tasks", "data": event_data})
            )
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("ws_events connection error")
    finally:
        _manager.disconnect(websocket)
        await pubsub.unsubscribe(EVENTS_CHANNEL_KEY)
        await pubsub.close()
        await r.aclose()
