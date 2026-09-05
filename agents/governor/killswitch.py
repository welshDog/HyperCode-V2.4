"""Global kill-switch. Redis flag for fast toggling; an off-box sentinel
file that a compromised process cannot clear; fail-closed if Redis can't
be reached (an unknowable kill state is a killed state)."""
from __future__ import annotations

import os

import redis_state

_KEY = "gov:kill"


def _sentinel_path() -> str:
    """Path to the off-box kill sentinel file (env-overridable for tests)."""
    return os.getenv("GOVERNOR_KILL_FILE", "/governance/KILL")


async def is_killed() -> bool:
    """True if the sentinel file exists, Redis has the kill flag set, or
    either check's health is unknowable (fails closed in all three cases).
    """
    # Path.exists() swallows OSError internally and returns False for the
    # whole ENOENT/ENOTDIR/ESTALE family, so wrapping it in try/except (the
    # previous approach) never actually caught anything -- a vanished mount
    # read as "no sentinel", not "unknowable, fail closed". os.stat() raises
    # instead, so we can tell those apart.
    #
    # Two stats, not one: os.stat(path) alone can't distinguish "parent
    # exists, file genuinely absent" from "parent itself is gone" -- both
    # raise FileNotFoundError. Stat the parent directory first so a missing
    # mount point fails closed instead of reading as "healthy, no sentinel".
    # This still can't catch every unmount shape -- a cleanly unmounted bind
    # mount can leave a present-but-empty directory at the mount point,
    # indistinguishable by stat alone from "healthy and no sentinel placed"
    # -- but it closes the parent-vanished and non-ENOENT fault cases that
    # Path.exists() silently ate.
    path = _sentinel_path()
    parent = os.path.dirname(path) or "."
    try:
        os.stat(parent)
    except OSError:
        return True  # parent (mount point) gone, stale, or unreadable
    try:
        os.stat(path)
        return True  # sentinel file exists
    except FileNotFoundError:
        pass  # parent is healthy; the file is genuinely absent
    except OSError:
        return True  # ENOTDIR, EACCES, ESTALE, etc. on the file itself
    try:
        return bool(await redis_state.get_redis().get(_KEY))
    except Exception:
        return True


async def engage(reason: str) -> None:
    """Set the Redis kill flag (does not touch the off-box sentinel file)."""
    await redis_state.get_redis().set(_KEY, reason or "engaged")


async def release(reason: str) -> None:
    """Clear the Redis kill flag. `reason` is accepted for call-site symmetry
    with `engage()` and audit logging upstream; the sentinel file, if
    present, still overrides this — deleting it is a separate, manual step.
    """
    await redis_state.get_redis().delete(_KEY)
