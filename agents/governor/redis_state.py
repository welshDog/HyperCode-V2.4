"""jti replay store + revocation set. Redis DB 3 (never 1/cache, never 2/rate-limits)."""
from __future__ import annotations

import os
from typing import Optional

import redis.asyncio as redis

_JTI = "gov:jti:"
_REVOKED_JTI = "gov:revoked:jti:"
_REVOKED_MISSION = "gov:revoked:mission:"

# Revocation keys only need to outlive a capability token's own lifetime
# (capability.mint()'s default ttl_seconds=300; the burn/replay window in
# main.py derives its TTL from that same expiry). 24h is a generous multiple
# with no security cost -- without a TTL these keys accumulated in Redis
# DB 3 for the life of the deployment (CodeRabbit follow-up).
_REVOCATION_TTL_SECONDS = 86_400

_r: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    """Return the module-wide Redis client, creating it on first use."""
    global _r
    if _r is None:
        url = os.getenv("GOVERNOR_REDIS_URL") or "redis://redis:6379/3"
        _r = redis.from_url(url, decode_responses=True)
    return _r


async def aclose() -> None:
    """Close the shared Redis client, if one was ever created."""
    global _r
    if _r is not None:
        # requirements.txt pins redis>=5.0.0 (floor only); .aclose() was
        # only added in redis-py 5.0.1, replacing the deprecated .close().
        # Tolerate either without touching the pin itself (CI can't verify
        # a pin change right now -- billing-locked) or the dependency graph.
        close = getattr(_r, "aclose", None) or _r.close
        await close()
        _r = None


async def register_use(jti: str, ttl_seconds: int) -> bool:
    """Record a `jti` as used, once. Returns False if it was already used
    (the `nx=True` set fails), enforcing single-use at the Redis level.
    """
    added = await get_redis().set(f"{_JTI}{jti}", "1", nx=True, ex=max(ttl_seconds, 1))
    return bool(added)


async def is_revoked(jti: str) -> bool:
    """True if this specific capability's `jti` has been revoked."""
    return bool(await get_redis().exists(f"{_REVOKED_JTI}{jti}"))


async def revoke(jti: str) -> None:
    """Add a `jti` to the revocation set for `_REVOCATION_TTL_SECONDS`."""
    await get_redis().set(f"{_REVOKED_JTI}{jti}", "1", ex=_REVOCATION_TTL_SECONDS)


async def revoke_mission(mission_id: str) -> None:
    """Revoke every capability for a whole mission, not just one `jti`."""
    await get_redis().set(f"{_REVOKED_MISSION}{mission_id}", "1", ex=_REVOCATION_TTL_SECONDS)


async def is_mission_revoked(mission_id: str) -> bool:
    """True if this mission has been mass-revoked via `revoke_mission()`."""
    return bool(await get_redis().exists(f"{_REVOKED_MISSION}{mission_id}"))
