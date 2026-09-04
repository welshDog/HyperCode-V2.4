"""System execution lease. The execution plane holds authority only while
this is valid. The governor renews it on a loop ONLY while the kill-switch
is clear and Shepherd is healthy — so a kill flip makes the whole
execution plane go inert within one lease period with no cooperation."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import killswitch
import redis_state

_KEY = "gov:lease"


async def current() -> Optional[dict]:
    try:
        raw = await redis_state.get_redis().get(_KEY)
        return json.loads(raw) if raw else None
    except Exception:
        return None


async def is_valid(now: Optional[datetime] = None) -> bool:
    now = now or datetime.now(timezone.utc)
    rec = await current()
    if not rec:
        return False
    return now < datetime.fromisoformat(rec["expires_at"])


async def renew_tick(*, shepherd_healthy: bool, ttl_seconds: int = 300, now: Optional[datetime] = None) -> bool:
    now = now or datetime.now(timezone.utc)
    if await killswitch.is_killed() or not shepherd_healthy:
        return False
    rec = {
        "lease_id": f"lease_{uuid.uuid4().hex}",
        "issued_at": now.isoformat(),
        "expires_at": (now + timedelta(seconds=ttl_seconds)).isoformat(),
    }
    try:
        await redis_state.get_redis().set(_KEY, json.dumps(rec), ex=ttl_seconds)
    except Exception:
        return False
    return True
