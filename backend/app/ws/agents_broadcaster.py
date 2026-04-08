"""
Task 3 — Agent Heartbeat Broadcaster
Provides:
  GET  /api/v1/agents/status  — list of agents with online/offline status
  WS   /api/v1/ws/agents      — real-time agent status broadcast (polls Redis every 5s)

Heartbeat protocol (agents write, this module reads):
  HSET agents:heartbeat:{agent_id}  name {name}  status {status}  last_seen {iso_ts}
  EXPIRE agents:heartbeat:{agent_id} 30          # 30s TTL → offline if missed 3 heartbeats

Any agent that publishes a heartbeat every 10s will be visible here.
Agents that miss their TTL disappear from KEYS — they show as "offline" for 5s then vanish.
"""

import asyncio
import datetime
import logging
from typing import List, Set

import redis.asyncio as aioredis
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


class AgentStatus(BaseModel):
    id: str
    name: str
    status: str          # "online" | "offline" | "busy" | "error"
    last_seen: str       # ISO timestamp


class AgentStatusList(BaseModel):
    agents: List[AgentStatus]
    updatedAt: str


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


async def _get_agent_statuses(r: aioredis.Redis) -> AgentStatusList:
    keys = await r.keys("agents:heartbeat:*")
    agents: List[AgentStatus] = []

    if keys:
        async with r.pipeline(transaction=False) as pipe:
            for key in keys:
                pipe.hgetall(key)
            heartbeats = await pipe.execute()

        for key, hb in zip(keys, heartbeats):
            if not hb:
                continue
            agent_id = key.split(":")[-1]
            agents.append(
                AgentStatus(
                    id=agent_id,
                    name=hb.get("name", agent_id),
                    status=hb.get("status", "online"),
                    last_seen=hb.get("last_seen", ""),
                )
            )

    return AgentStatusList(
        agents=agents,
        updatedAt=datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    )


@router.get("/agents/status", response_model=AgentStatusList)
@router.get("/agents", response_model=AgentStatusList)
async def get_agent_status() -> AgentStatusList:
    """REST endpoint — returns current agent heartbeat status from Redis.
    Aliased at both /agents/status and /agents for dashboard compatibility."""
    r = await aioredis.from_url(settings.HYPERCODE_REDIS_URL, decode_responses=True)
    try:
        return await _get_agent_statuses(r)
    finally:
        await r.aclose()


@router.websocket("/ws/agents")
async def ws_agents(websocket: WebSocket) -> None:
    """
    WebSocket — broadcasts AgentStatusList every 5 seconds.
    Clients connect to ws://hypercode-core:8000/api/v1/ws/agents
    """
    await _manager.connect(websocket)
    r = await aioredis.from_url(settings.HYPERCODE_REDIS_URL, decode_responses=True)
    try:
        while True:
            payload = await _get_agent_statuses(r)
            await websocket.send_text(payload.model_dump_json())
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("ws_agents connection error")
    finally:
        _manager.disconnect(websocket)
        await r.aclose()
