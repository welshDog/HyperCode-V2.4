"""
Task 2 — Metrics Broadcaster
Provides:
  GET  /api/v1/metrics       — REST snapshot (MetricsSnapshot)
  WS   /api/v1/ws/metrics    — 5-second broadcast loop per connected client

Redis keys consumed (written by Task 10 HTTP middleware):
  req_count:{YYYYMMHHMM}     — request count per minute (TTL 120s)
  error_count:{YYYYMMHHMM}   — error count per minute   (TTL 120s)
  response_times             — LPUSH list of last 100 elapsed_ms values

Redis keys written by other agents:
  healer:heals_today         — integer reset at midnight by healer-agent
  hypercode:task_queue       — LIST used as task backlog (LLEN = queue depth)
  agents:heartbeat:*         — HSET by each agent every 10s (Task 3), KEYS count = active agents
"""

import asyncio
import datetime
import logging
from typing import Set

import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


class MetricsSnapshot(BaseModel):
    requestsPerMin: int
    avgResponseMs: float
    healsToday: int
    errorRatePct: float
    activeAgents: int
    redisQueueDepth: int
    collectedAt: str


class ConnectionManager:
    """Tracks connected WebSocket clients for broadcast."""

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


async def _build_snapshot(r: aioredis.Redis) -> MetricsSnapshot:
    now = datetime.datetime.utcnow()
    minute_key = now.strftime("%Y%m%d%H%M")
    prev_key = (now - datetime.timedelta(minutes=1)).strftime("%Y%m%d%H%M")

    async with r.pipeline(transaction=False) as pipe:
        pipe.get(f"req_count:{minute_key}")
        pipe.get(f"req_count:{prev_key}")
        pipe.lrange("response_times", 0, 99)
        pipe.get(f"error_count:{minute_key}")
        pipe.get("healer:heals_today")
        pipe.llen("hypercode:task_queue")
        pipe.keys("agents:heartbeat:*")
        results = await pipe.execute()

    req_cur = int(results[0] or 0)
    req_prev = int(results[1] or 0)
    requests_per_min = req_cur + req_prev  # rolling ~2-min window

    times = [float(t) for t in (results[2] or [])]
    avg_ms = round(sum(times) / len(times), 2) if times else 0.0

    error_cur = int(results[3] or 0)
    error_pct = round((error_cur / req_cur * 100) if req_cur > 0 else 0.0, 2)

    heals_today = int(results[4] or 0)
    queue_depth = int(results[5] or 0)
    active_agents = len(results[6] or [])

    return MetricsSnapshot(
        requestsPerMin=requests_per_min,
        avgResponseMs=avg_ms,
        healsToday=heals_today,
        errorRatePct=error_pct,
        activeAgents=active_agents,
        redisQueueDepth=queue_depth,
        collectedAt=now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


@router.get("/metrics", response_model=MetricsSnapshot)
async def get_metrics() -> MetricsSnapshot:
    """REST endpoint — returns a single MetricsSnapshot from live Redis data."""
    r = await aioredis.from_url(settings.HYPERCODE_REDIS_URL, decode_responses=True)
    try:
        return await _build_snapshot(r)
    finally:
        await r.aclose()


@router.websocket("/ws/metrics")
async def ws_metrics(websocket: WebSocket) -> None:
    """
    WebSocket — broadcasts MetricsSnapshot JSON every 5 seconds.
    Clients connect to ws://hypercode-core:8000/api/v1/ws/metrics
    """
    await _manager.connect(websocket)
    r = await aioredis.from_url(settings.HYPERCODE_REDIS_URL, decode_responses=True)
    try:
        while True:
            snapshot = await _build_snapshot(r)
            await websocket.send_text(snapshot.model_dump_json())
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("ws_metrics connection error")
    finally:
        _manager.disconnect(websocket)
        await r.aclose()
