"""jti replay store + revocation set. Redis DB 3 (never 1/cache, never 2/rate-limits)."""
from __future__ import annotations

import os
from typing import Optional

import redis.asyncio as redis

_JTI = "gov:jti:"
_REVOKED_JTI = "gov:revoked:jti:"
_REVOKED_MISSION = "gov:revoked:mission:"

_r: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    global _r
    if _r is None:
        url = os.getenv("GOVERNOR_REDIS_URL") or "redis://redis:6379/3"
        _r = redis.from_url(url, decode_responses=True)
    return _r


async def aclose() -> None:
    global _r
    if _r is not None:
        await _r.aclose()
        _r = None


async def register_use(jti: str, ttl_seconds: int) -> bool:
    added = await get_redis().set(f"{_JTI}{jti}", "1", nx=True, ex=max(ttl_seconds, 1))
    return bool(added)


async def is_revoked(jti: str) -> bool:
    return bool(await get_redis().exists(f"{_REVOKED_JTI}{jti}"))


async def revoke(jti: str) -> None:
    await get_redis().set(f"{_REVOKED_JTI}{jti}", "1")


async def revoke_mission(mission_id: str) -> None:
    await get_redis().set(f"{_REVOKED_MISSION}{mission_id}", "1")


async def is_mission_revoked(mission_id: str) -> bool:
    return bool(await get_redis().exists(f"{_REVOKED_MISSION}{mission_id}"))
