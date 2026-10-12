"""Pressure signal + pause/resume planning for throttle-agent. Pure and stdlib-only, so it is unit-tested without Docker.

The old "RAM %" was the sum of ~16 hard-coded containers divided by Docker's total: blind to the other agents, the page
cache, swap and the Windows HOST. On 2026-10-03 the host hit 1 MB free (Memory Compression 4.5 GB) while that number would
have read "fine". The signal now comes from `scripts/ram_guard.py --json --out FILE --loop 30` running on the HOST, which
sees host + WSL. The file is mounted read-only into this container.

Rules (each has a test):
  * A missing, stale, unreadable or invalid signal is UNKNOWN, and UNKNOWN NEVER triggers a pause (never act blind).
  * AMBER pauses tier 6, RED pauses tiers 6, 5, 4. Tiers in the protect set are never paused.
  * Debounce (added after observe mode caught a flaky WSL read and a compression value flickering around its threshold):
    AMBER must be seen in N consecutive NEW samples (default 3) before it acts; RED acts after 1. Re-reading the same
    file between host writes is not a new sample. GREEN or UNKNOWN resets the streaks.
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
    mtime: Optional[float] = None  # when the host wrote it: identifies a NEW sample (the agent polls more often than the host writes)


def _int(v: Any) -> Optional[int]:
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def read_signal(path: str, now: Optional[float] = None, max_age_s: float = 120.0) -> Signal:
    """The host guard's latest verdict, or UNKNOWN (never a guess)."""
    now = time.time() if now is None else now
    try:
        mtime = os.path.getmtime(path)  # file mtime: no timezone parsing to get wrong
    except OSError:
        return Signal(UNKNOWN, "signal file missing")
    age = max(0.0, now - mtime)
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return Signal(UNKNOWN, "signal file unreadable", age_s=age, mtime=mtime)
    if not isinstance(data, dict) or data.get("overall") not in KNOWN:
        return Signal(UNKNOWN, "signal has no valid 'overall'", age_s=age, mtime=mtime)
    if age > max_age_s:
        return Signal(UNKNOWN, f"signal stale ({int(age)}s old, max {int(max_age_s)}s)", age_s=age, mtime=mtime)
    m = data.get("metrics") if isinstance(data.get("metrics"), dict) else {}
    return Signal(data["overall"], "fresh", age, _int(m.get("host_free_mb")), _int(m.get("wsl_avail_mb")),
                  _int(m.get("compression_mb")), mtime)


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


PENDING = "PENDING"  # non-GREEN, but not yet seen often enough (debounce) to act on


@dataclass(frozen=True)
class Step:
    level: str
    to_pause: tuple[int, ...]
    to_resume: tuple[int, ...]
    protected_skipped: tuple[int, ...]
    green_since: Optional[float]
    effective: str = GREEN  # what the debounce let through: RED / AMBER / PENDING / GREEN / UNKNOWN
    amber_streak: int = 0   # consecutive NEW samples that were AMBER or RED
    red_streak: int = 0     # consecutive NEW samples that were RED


def step(level: str, paused: set[int], protect_tiers: set[int], tiers: dict[int, list[str]],
         green_since: Optional[float], now: float, hold_s: float,
         amber_streak: int = 0, red_streak: int = 0, amber_cycles: int = 1, red_cycles: int = 1,
         new_sample: bool = True) -> Step:
    """One decision. `paused` = tiers this agent currently holds paused (real, or simulated in observe mode).

    Debounce: a flaky reading must not trigger a pause. AMBER (or worse) must be seen in `amber_cycles` consecutive
    NEW samples before it acts; RED acts after `red_cycles` consecutive RED samples. `new_sample=False` (the same file
    read again between host writes) does not advance the streaks. GREEN or UNKNOWN resets them. The defaults (1, 1) keep
    the original "act on the first reading" behaviour.
    """
    if level in (AMBER, RED):
        a = amber_streak + (1 if new_sample else 0)
        r = (red_streak + (1 if new_sample else 0)) if level == RED else 0
    else:
        a = r = 0

    if level == RED and r >= max(1, red_cycles):
        effective = RED
    elif level in (AMBER, RED) and a >= max(1, amber_cycles):
        effective = AMBER
    elif level in (AMBER, RED):
        effective = PENDING
    else:
        effective = level  # GREEN or UNKNOWN

    desired = _DESIRED.get(effective, ())  # PENDING and UNKNOWN pause nothing
    protected = tuple(t for t in desired if t in protect_tiers)
    to_pause = tuple(t for t in desired if t in tiers and t not in protect_tiers and t not in paused)
    gs: Optional[float] = None
    to_resume: tuple[int, ...] = ()
    if level == GREEN:
        gs = green_since if green_since is not None else now
        if paused and now - gs >= hold_s:
            to_resume = tuple(sorted(paused))
    # any non-GREEN level (including UNKNOWN and PENDING) restarts the hold: never resume on a signal that is not clearly calm
    return Step(level, to_pause, to_resume, protected, gs, effective, a, r)
