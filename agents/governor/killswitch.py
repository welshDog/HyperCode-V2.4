"""Global kill-switch. Redis flag for fast toggling; an off-box sentinel
file that a compromised process cannot clear; fail-closed if Redis can't
be reached (an unknowable kill state is a killed state)."""
from __future__ import annotations

import os
from pathlib import Path

import redis_state

_KEY = "gov:kill"


def _sentinel_path() -> str:
    return os.getenv("GOVERNOR_KILL_FILE", "/governance/KILL")


async def is_killed() -> bool:
    if Path(_sentinel_path()).exists():
        return True
    try:
        return bool(await redis_state.get_redis().get(_KEY))
    except Exception:
        return True


async def engage(reason: str) -> None:
    await redis_state.get_redis().set(_KEY, reason or "engaged")


async def release(reason: str) -> None:
    await redis_state.get_redis().delete(_KEY)
