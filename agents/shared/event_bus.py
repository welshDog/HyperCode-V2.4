"""
HyperCode V2.0 — Redis Agent Event Bus
=======================================
Async pub/sub backbone for all agent-to-agent communication.
One AgentEventBus instance per agent process.

Usage:
    # In your agent startup:
    bus = AgentEventBus()
    await bus.connect()

    # Publish an event:
    await bus.publish(AgentMessage(
        agent_id="healer-01",
        agent_type="healer",
        status="success",
        xp_earned=50,
    ))

    # Subscribe to all events:
    async def my_handler(msg: AgentMessage):
        print(msg.summary())

    await bus.subscribe(my_handler)

    # FastAPI dependency:
    bus: AgentEventBus = Depends(get_event_bus)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Awaitable, Callable

import redis.asyncio as aioredis

from .agent_message import (
    AgentMessage,
    REDIS_CHANNEL_ALL_EVENTS,
    REDIS_KEY_EVENT_LOG,
)

logger = logging.getLogger("hypercode.event_bus")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
EVENT_LOG_MAX_SIZE = int(os.getenv("EVENT_LOG_MAX_SIZE", "1000"))


class AgentEventBus:
    """Async Redis pub/sub bus. One instance per agent process."""

    def __init__(self, redis_url: str = REDIS_URL) -> None:
        self._url = redis_url
        self._redis: aioredis.Redis | None = None
        self._pubsub: aioredis.client.PubSub | None = None
        self._connected = False

    # ── Connection ─────────────────────────────────────────────────────────────
    async def connect(self) -> None:
        """Connect to Redis. Call once on agent startup."""
        try:
            self._redis = aioredis.from_url(
                self._url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )
            await self._redis.ping()
            self._connected = True
            logger.info("✅ AgentEventBus connected to %s", self._url)
        except Exception as exc:
            logger.error("❌ Redis connection failed: %s", exc)
            raise

    async def disconnect(self) -> None:
        """Graceful shutdown. Call on agent teardown."""
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.aclose()
        if self._redis:
            await self._redis.aclose()
        self._connected = False
        logger.info("AgentEventBus disconnected.")

    # ── Publish ─────────────────────────────────────────────────────────────────
    async def publish(
        self,
        message: AgentMessage,
        channel: str = REDIS_CHANNEL_ALL_EVENTS,
        persist: bool = True,
    ) -> int:
        """
        Publish an AgentMessage to Redis.
        Returns the number of subscribers who received it.
        If persist=True, also appends to the event log list.
        """
        if not self._redis:
            raise RuntimeError("Event bus not connected. Call connect() first.")

        payload = message.to_redis_payload()

        # Pub/sub broadcast
        count = await self._redis.publish(channel, payload)

        # Persistent log (capped at EVENT_LOG_MAX_SIZE)
        if persist:
            pipe = self._redis.pipeline()
            log_key = f"{REDIS_KEY_EVENT_LOG}:{message.agent_type}"
            pipe.lpush(log_key, payload)
            pipe.ltrim(log_key, 0, EVENT_LOG_MAX_SIZE - 1)
            pipe.lpush(f"{REDIS_KEY_EVENT_LOG}:all", payload)
            pipe.ltrim(f"{REDIS_KEY_EVENT_LOG}:all", 0, EVENT_LOG_MAX_SIZE - 1)
            await pipe.execute()

        logger.debug(
            "📤 [%s → %s] %s | XP+%d",
            message.agent_id, channel, message.status, message.xp_earned
        )
        return count

    # ── Subscribe ────────────────────────────────────────────────────────────────
    async def subscribe(
        self,
        handler: Callable[[AgentMessage], Awaitable[None]],
        channel: str = REDIS_CHANNEL_ALL_EVENTS,
    ) -> None:
        """
        Subscribe to a channel and call handler for each message.
        Runs forever with automatic reconnection — wrap in asyncio.create_task() for background listening.
        """
        while True:
            try:
                if not self._redis:
                    raise RuntimeError("Event bus not connected. Call connect() first.")

                self._pubsub = self._redis.pubsub()
                await self._pubsub.subscribe(channel)
                logger.info("📥 Subscribed to channel: %s", channel)

                async for raw_message in self._pubsub.listen():
                    if raw_message["type"] == "message":
                        try:
                            msg = AgentMessage.from_redis_payload(raw_message["data"])
                            await handler(msg)
                        except Exception as exc:
                            logger.error("❌ Handler error: %s | raw: %s", exc, raw_message["data"][:120])
            except Exception as exc:
                logger.warning("⚠️ Redis subscription dropped: %s. Reconnecting in 3s...", exc)
                await asyncio.sleep(3)
                try:
                    await self.connect()
                except Exception:
                    pass

    # ── XP Ledger ────────────────────────────────────────────────────────────────
    async def award_xp(
        self,
        agent_id: str,
        xp: int,
        coins: float = 0.0,
    ) -> dict[str, float]:
        """
        Increment XP + BROski$ for an agent in Redis.
        Returns the new totals.
        """
        if not self._redis:
            raise RuntimeError("Event bus not connected.")

        pipe = self._redis.pipeline()
        xp_key = f"hypercode:xp:{agent_id}"
        coins_key = f"hypercode:coins:{agent_id}"
        pipe.incrbyfloat(xp_key, xp)
        pipe.incrbyfloat(coins_key, coins)
        results = await pipe.execute()

        return {"xp_total": float(results[0]), "coins_total": float(results[1])}

    async def get_agent_xp(
        self,
        agent_id: str,
    ) -> dict[str, float | int]:
        """Get current XP, coins, and level for an agent."""
        from .agent_message import xp_to_level

        if not self._redis:
            raise RuntimeError("Event bus not connected.")

        xp    = float(await self._redis.get(f"hypercode:xp:{agent_id}") or 0)
        coins = float(await self._redis.get(f"hypercode:coins:{agent_id}") or 0)

        return {
            "agent_id":    agent_id,
            "xp_total":    xp,
            "coins_total": coins,
            "level":       xp_to_level(int(xp)),
        }

    # ── Event History ─────────────────────────────────────────────────────────
    async def get_event_history(
        self,
        agent_type: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Fetch recent events from the persistent log."""
        if not self._redis:
            raise RuntimeError("Event bus not connected.")

        key = (
            f"{REDIS_KEY_EVENT_LOG}:{agent_type}"
            if agent_type
            else f"{REDIS_KEY_EVENT_LOG}:all"
        )
        raw_events = await self._redis.lrange(key, 0, limit - 1)
        return [json.loads(e) for e in raw_events]


# ── FastAPI singleton dependency ───────────────────────────────────────────────
_bus_instance: AgentEventBus | None = None
_bus_lock = asyncio.Lock()


async def get_event_bus() -> AgentEventBus:
    """
    Get or create the singleton AgentEventBus.
    Use as a FastAPI dependency:

        @router.get("/status")
        async def status(bus: AgentEventBus = Depends(get_event_bus)):
            ...
    """
    global _bus_instance
    async with _bus_lock:
        if _bus_instance is None or not _bus_instance._connected:
            _bus_instance = AgentEventBus()
            await _bus_instance.connect()
    return _bus_instance
