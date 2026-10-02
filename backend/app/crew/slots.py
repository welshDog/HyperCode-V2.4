"""RAM-aware slot gate: at most N crew agents awake at once, and never below a RAM floor.

This box has a ~4 GB ceiling (see WHATS_DONE N22): the cap and the floor exist so a crew run
waits instead of taking the machine down. Single-process by design — hypercode-core runs flows
in one asyncio loop — so a counter + short polling sleep is enough, and it never binds to an
event loop (tests create many).

Fail behaviour: when slots or RAM stay unavailable past the timeout we raise
:class:`SlotUnavailable` (the node fails; nothing is dispatched). When RAM cannot be *read*
at all we rely on the cap alone rather than blocking every run.
"""

from __future__ import annotations

import asyncio
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Callable, Optional

HARD_MAX_AWAKE = 3
DEFAULT_MIN_AVAILABLE_MB = 1200  # the documented "keep >= 1.2 GB available" floor
DEFAULT_TIMEOUT_S = 120.0
_POLL_S = 0.05


class SlotUnavailable(RuntimeError):
    """No slot (or not enough free RAM) within the timeout. Message is safe to show."""


@dataclass(frozen=True)
class SlotTicket:
    wait_ms: int
    available_mb: Optional[int]


def read_available_mb(path: str = "/proc/meminfo") -> Optional[int]:
    """``MemAvailable`` in MB, or None when it cannot be read (non-Linux, no /proc)."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


class SlotGate:
    def __init__(
        self,
        cap: int = HARD_MAX_AWAKE,
        min_available_mb: int = DEFAULT_MIN_AVAILABLE_MB,
        ram_reader: Callable[[], Optional[int]] = read_available_mb,
        poll_s: float = _POLL_S,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.cap = max(1, min(int(cap), HARD_MAX_AWAKE))
        self.min_available_mb = max(0, int(min_available_mb))
        self._ram_reader = ram_reader
        self._poll_s = poll_s
        self._clock = clock
        self._active = 0

    @property
    def active(self) -> int:
        return self._active

    def _ram_ok(self) -> tuple[bool, Optional[int]]:
        if self.min_available_mb == 0:
            return True, None
        available = self._ram_reader()
        if available is None:  # unreadable: rely on the cap alone
            return True, None
        return available >= self.min_available_mb, available

    async def acquire(self, timeout_s: float = DEFAULT_TIMEOUT_S) -> SlotTicket:
        start = self._clock()
        deadline = start + timeout_s
        reason = "all crew slots are busy"
        while True:
            if self._active < self.cap:
                ok, available = self._ram_ok()
                if ok:
                    self._active += 1  # no await between check and take: atomic on one loop
                    return SlotTicket(int((self._clock() - start) * 1000), available)
                reason = "free RAM is below the safety floor"
            else:
                reason = "all crew slots are busy"
            if self._clock() >= deadline:
                raise SlotUnavailable(f"no crew slot: {reason}")
            await asyncio.sleep(self._poll_s)

    def release(self) -> None:
        self._active = max(0, self._active - 1)

    @asynccontextmanager
    async def slot(self, timeout_s: float = DEFAULT_TIMEOUT_S) -> AsyncIterator[SlotTicket]:
        ticket = await self.acquire(timeout_s)
        try:
            yield ticket
        finally:
            self.release()


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def gate_from_env() -> SlotGate:
    return SlotGate(
        cap=_env_int("CREW_MAX_AWAKE", HARD_MAX_AWAKE),
        min_available_mb=_env_int("CREW_MIN_AVAILABLE_MB", DEFAULT_MIN_AVAILABLE_MB),
    )


def slot_timeout_s() -> float:
    return float(max(1, _env_int("CREW_SLOT_TIMEOUT_S", int(DEFAULT_TIMEOUT_S))))


_GATE: Optional[SlotGate] = None


def get_slot_gate() -> SlotGate:
    global _GATE
    if _GATE is None:
        _GATE = gate_from_env()
    return _GATE


def set_slot_gate(gate: Optional[SlotGate]) -> None:
    """Replace (or with None, reset) the process-wide gate. For tests and ops tooling."""
    global _GATE
    _GATE = gate
