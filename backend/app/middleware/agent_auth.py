"""
Phase 10D — Agent API key auth + per-agent Redis rate limiting.

Internal agents (healer, crew-orchestrator, agent-x, etc.) include
  X-Agent-Key: hc_<token>
in requests to hypercode-core. This module:
  1. Validates the key against the agent_api_keys table (SHA-256 hash comparison).
  2. Applies a per-agent sliding-window rate limit via Redis.
  3. Provides two FastAPI dependencies:
       - get_agent_from_key  → returns agent dict or None (optional auth)
       - require_agent_key   → raises 401 if no key, 403 if invalid
"""
from __future__ import annotations

import hashlib
import logging
import os
import secrets
import time
from typing import Annotated, Optional

import redis.asyncio as aioredis
from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import text

from app.db.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

_REDIS_URL: str = os.getenv("HYPERCODE_REDIS_URL", "redis://redis:6379/0")
_redis_client: Optional[aioredis.Redis] = None


def _get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            _REDIS_URL, decode_responses=True, socket_connect_timeout=2
        )
    return _redis_client


# ── Key helpers ───────────────────────────────────────────────────────────────

def generate_agent_key() -> str:
    """Return a new hc_-prefixed agent API key (43 chars + 3 prefix = 46 total)."""
    return "hc_" + secrets.token_urlsafe(32)


def hash_agent_key(raw: str) -> str:
    """Return the SHA-256 hex digest of a raw agent key."""
    return hashlib.sha256(raw.encode()).hexdigest()


# ── Per-agent rate limiting (Redis sliding window, 1-minute buckets) ──────────

async def _check_agent_rate_limit(agent_name: str, rpm_limit: int) -> bool:
    """Return True if agent is within its rate limit, False if exceeded."""
    try:
        r = _get_redis()
        minute = int(time.time()) // 60
        key = f"agent_rl:{agent_name}:{minute}"
        count = await r.incr(key)
        if count == 1:
            # 2-minute TTL so the key expires cleanly after the window rolls
            await r.expire(key, 120)
        return count <= rpm_limit
    except Exception as exc:
        # Fail open — never block agents when Redis is temporarily unavailable
        logger.warning("Agent rate-limit Redis error (allowing through): %s", exc)
        return True


# ── FastAPI dependencies ──────────────────────────────────────────────────────

async def get_agent_from_key(
    request: Request,  # noqa: ARG001 — reserved for future IP allow-listing
    x_agent_key: Annotated[Optional[str], Header()] = None,
    x_api_key: Annotated[Optional[str], Header(alias="X-API-Key")] = None,
) -> Optional[dict]:
    """Optional agent key auth.

    Returns:
        dict with ``agent_name`` and ``rate_limit_rpm`` if the key is valid.
        None if the header is absent.
    Raises:
        403 on an invalid / revoked key.
        429 if the agent has exceeded its rate limit.
        503 if the auth DB is temporarily unavailable.
    """
    raw_key = x_agent_key or x_api_key
    if not raw_key:
        return None

    key_hash = hash_agent_key(raw_key)

    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("""
                    SELECT agent_name, rate_limit_rpm
                    FROM   agent_api_keys
                    WHERE  key_hash  = :h
                    AND    is_active = true
                """),
                {"h": key_hash},
            )
            row = result.mappings().first()
    except Exception as exc:
        logger.error("Agent key DB lookup failed: %s", exc)
        raise HTTPException(status_code=503, detail="Auth service temporarily unavailable")

    if not row:
        raise HTTPException(status_code=403, detail="Invalid or revoked agent key")

    agent = dict(row)
    allowed = await _check_agent_rate_limit(agent["agent_name"], agent["rate_limit_rpm"])
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Agent rate limit exceeded ({agent['rate_limit_rpm']} rpm)",
            headers={"Retry-After": "60"},
        )

    return agent


async def require_agent_key(
    agent: Optional[dict] = Depends(get_agent_from_key),
) -> dict:
    """Strict version — raises 401 if X-Agent-Key header is absent."""
    if agent is None:
        raise HTTPException(
            status_code=401,
            detail="X-Agent-Key header required for this endpoint",
        )
    return agent
