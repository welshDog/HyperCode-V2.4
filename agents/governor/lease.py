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
    """Return the current lease record, or None if absent/unreachable."""
    try:
        raw = await redis_state.get_redis().get(_KEY)
        return json.loads(raw) if raw else None
    except Exception:
        return None


async def is_valid(now: Optional[datetime] = None) -> bool:
    """True only if a lease exists, has a well-formed timezone-aware
    `expires_at`, and hasn't expired. Any malformed record reads as invalid
    rather than raising, so a corrupted Redis record fails closed.
    """
    now = now or datetime.now(timezone.utc)
    rec = await current()
    if not rec:
        return False
    # CodeRabbit follow-up: a malformed record (missing/non-string/
    # unparsable expires_at) previously raised straight through -- main.py
    # calls this unguarded on the LIVE mint path, so a corrupted Redis
    # record would 500 the request instead of cleanly refusing it, same
    # bug class as everywhere else in this codebase that fails closed. A
    # naive (tzinfo-less) timestamp can't be safely compared to an
    # aware `now` either -- treat it the same as invalid, not "expired
    # sometime, who knows."
    try:
        expires_at = datetime.fromisoformat(rec["expires_at"])
    except (KeyError, TypeError, ValueError):
        return False
    if expires_at.tzinfo is None:
        return False
    return now < expires_at


async def renew_tick(*, shepherd_healthy: bool, ttl_seconds: int = 300, now: Optional[datetime] = None) -> bool:
    """Issue a fresh lease for `ttl_seconds`, unless killed or Shepherd is
    unhealthy. Returns whether the renewal actually happened.
    """
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
