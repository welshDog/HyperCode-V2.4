"""Pressure signal + pause/resume planning for throttle-agent. Pure and stdlib-only, so it is unit-tested without Docker.

The old "RAM %" was the sum of ~16 hard-coded containers divided by Docker's total: blind to the other agents, the page
cache, swap and the Windows HOST. On 2026-10-03 the host hit 1 MB free (Memory Compression 4.5 GB) while that number would
have read "fine". The signal now comes from `scripts/ram_guard.py --json --out FILE --loop 30` running on the HOST, which
sees host + WSL. The file is mounted read-only into this container.

Rules (each has a test):
  * A missing, stale, unreadable or invalid signal is UNKNOWN, and UNKNOWN NEVER triggers a pause (never act blind).
  * AMBER pauses tier 6, RED pauses tiers 6, 5, 4. Tiers in the protect set are never paused.
  * Resume only after the signal has been GREEN, continuously, for the hold time (hysteresis). Any other level restarts it.
  * Note `docker pause` freezes processes but does NOT free their RAM; it removes CPU load and lets the kernel swap cold pages.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

GREEN, AMBER, RED, UNKNOWN = "GREEN", "AMBER", "RED", "UNKNOWN"
KNOWN = (GREEN, AMBER, RED)

# tier numbers to pause at each level (the highest tier number is the cheapest to lose)
_DESIRED: dict[str, tuple[int, ...]] = {GREEN: (), AMBER: (6,), RED: (6, 5, 4), UNKNOWN: ()}


@dataclass(frozen=True)
class Signal:
    level: str
    reason: str
    age_s: Optional[float] = None
    host_free_mb: Optional[int] = None
    wsl_avail_mb: Optional[int] = None
    compression_mb: Optional[int] = None


def _int(v: Any) -> Optional[int]:
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def read_signal(path: str, now: Optional[float] = None, max_age_s: float = 120.0) -> Signal:
    """The host guard's latest verdict, or UNKNOWN (never a guess)."""
    now = time.time() if now is None else now
    try:
        age = max(0.0, now - os.path.getmtime(path))  # file mtime: no timezone parsing to get wrong
    except OSError:
        return Signal(UNKNOWN, "signal file missing")
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return Signal(UNKNOWN, "signal file unreadable", age_s=age)
    if not isinstance(data, dict) or data.get("overall") not in KNOWN:
        return Signal(UNKNOWN, "signal has no valid 'overall'", age_s=age)
    if age > max_age_s:
        return Signal(UNKNOWN, f"signal stale ({int(age)}s old, max {int(max_age_s)}s)", age_s=age)
    m = data.get("metrics") if isinstance(data.get("metrics"), dict) else {}
    return Signal(data["overall"], "fresh", age, _int(m.get("host_free_mb")), _int(m.get("wsl_avail_mb")),
                  _int(m.get("compression_mb")))


def parse_tiers(raw: Optional[str], default: dict[int, list[str]]) -> dict[int, list[str]]:
    """THROTTLE_TIERS_JSON: {"6": ["cadvisor"], ...}. Anything invalid falls back to the defaults (never half-applies)."""
    if not raw or not raw.strip():
        return default
    try:
        data = json.loads(raw)
        if not isinstance(data, dict) or not data:
            return default
        out: dict[int, list[str]] = {}
        for k, v in data.items():
            tier = int(k)
            if tier < 1 or not isinstance(v, list) or not all(isinstance(n, str) and n.strip() for n in v):
                return default
            out[tier] = [n.strip() for n in v]
        return out
    except (ValueError, TypeError):
        return default


@dataclass(frozen=True)
class Step:
    level: str
    to_pause: tuple[int, ...]
    to_resume: tuple[int, ...]
    protected_skipped: tuple[int, ...]
    green_since: Optional[float]


def step(level: str, paused: set[int], protect_tiers: set[int], tiers: dict[int, list[str]],
         green_since: Optional[float], now: float, hold_s: float) -> Step:
    """One decision. `paused` = tiers this agent currently holds paused (real, or simulated in observe mode)."""
    desired = _DESIRED.get(level, ())
    protected = tuple(t for t in desired if t in protect_tiers)
    to_pause = tuple(t for t in desired if t in tiers and t not in protect_tiers and t not in paused)
    gs: Optional[float] = None
    to_resume: tuple[int, ...] = ()
    if level == GREEN:
        gs = green_since if green_since is not None else now
        if paused and now - gs >= hold_s:
            to_resume = tuple(sorted(paused))
    # any non-GREEN level (including UNKNOWN) restarts the hold: never resume on a signal that is not clearly calm
    return Step(level, to_pause, to_resume, protected, gs)
