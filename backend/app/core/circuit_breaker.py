"""
HyperCode V2.4 — Async Circuit Breaker
Gordon Tier 2 Step 4

Prevents cascading failures when external services (LLM router, crew-orchestrator,
Stripe) become slow or unavailable. State machine: CLOSED → OPEN → HALF_OPEN → CLOSED.

Usage (async callsite):
    from app.core.circuit_breaker import get_breaker

    _breaker = get_breaker("my-service", fail_max=3, reset_timeout=30)

    result = await _breaker.call(some_async_fn, arg1, kwarg=val)

Usage (sync callsite):
    result = _breaker.call_sync(some_sync_fn, arg1, kwarg=val)
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from enum import Enum
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED    = "closed"      # Normal — calls pass through
    OPEN      = "open"        # Failing — reject immediately (fail fast)
    HALF_OPEN = "half_open"   # One probe allowed to test recovery


class CircuitBreakerOpen(Exception):
    """Raised when a call is rejected because the circuit is OPEN."""
    def __init__(self, name: str, reset_in: float) -> None:
        self.name = name
        self.reset_in = reset_in
        super().__init__(f"Circuit {name!r} OPEN — retry in {reset_in:.0f}s")


class HyperCircuitBreaker:
    """
    Async-native circuit breaker.  Thread-safe via asyncio.Lock (async path)
    or threading.Lock (sync path).  Both paths share the same state variables.

    State transitions:
        CLOSED  → OPEN      after fail_max consecutive failures
        OPEN    → HALF_OPEN after reset_timeout seconds
        HALF_OPEN → CLOSED  on first success
        HALF_OPEN → OPEN    on first failure
    """

    def __init__(self, name: str, fail_max: int = 5, reset_timeout: int = 30) -> None:
        self.name = name
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout
        self._failures: int = 0
        self._state: CircuitState = CircuitState.CLOSED
        self._opened_at: float = 0.0
        self._async_lock = asyncio.Lock()
        self._sync_lock  = threading.Lock()

    # ── Public properties ─────────────────────────────────────────────────────

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failures

    # ── Async call ────────────────────────────────────────────────────────────

    async def call(
        self,
        func: Callable[..., Coroutine[Any, Any, Any]],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """
        Call an async function through the circuit breaker.
        Raises CircuitBreakerOpen immediately if the circuit is OPEN.
        """
        await self._async_maybe_half_open()

        try:
            result = await func(*args, **kwargs)
            await self._async_on_success()
            return result
        except CircuitBreakerOpen:
            raise
        except Exception as exc:
            await self._async_on_failure(exc)
            raise

    # ── Sync call ─────────────────────────────────────────────────────────────

    def call_sync(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        Call a synchronous function through the circuit breaker.
        Raises CircuitBreakerOpen immediately if the circuit is OPEN.
        """
        self._sync_maybe_half_open()

        try:
            result = func(*args, **kwargs)
            self._sync_on_success()
            return result
        except CircuitBreakerOpen:
            raise
        except Exception as exc:
            self._sync_on_failure(exc)
            raise

    # ── State snapshot (for health endpoints) ────────────────────────────────

    def as_dict(self) -> dict:
        remaining = max(0.0, self._opened_at + self.reset_timeout - time.monotonic())
        return {
            "name": self.name,
            "state": self._state.value,
            "failures": self._failures,
            "fail_max": self.fail_max,
            "reset_timeout_s": self.reset_timeout,
            "reset_in_s": round(remaining, 1) if self._state == CircuitState.OPEN else 0,
        }

    # ── Async internals ───────────────────────────────────────────────────────

    async def _async_maybe_half_open(self) -> None:
        async with self._async_lock:
            if self._state == CircuitState.OPEN:
                remaining = self._opened_at + self.reset_timeout - time.monotonic()
                if remaining > 0:
                    raise CircuitBreakerOpen(self.name, remaining)
                self._state = CircuitState.HALF_OPEN
                logger.info("Circuit %r → HALF_OPEN (probing recovery)", self.name)

    async def _async_on_success(self) -> None:
        async with self._async_lock:
            if self._state == CircuitState.HALF_OPEN:
                logger.info("Circuit %r → CLOSED (probe succeeded)", self.name)
            self._state = CircuitState.CLOSED
            self._failures = 0

    async def _async_on_failure(self, exc: Exception) -> None:
        async with self._async_lock:
            self._failures += 1
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
                logger.warning("Circuit %r → OPEN (probe failed: %s)", self.name, exc)
            elif self._failures >= self.fail_max:
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
                logger.warning(
                    "Circuit %r → OPEN (%d/%d failures: %s)",
                    self.name, self._failures, self.fail_max, exc,
                )

    # ── Sync internals ────────────────────────────────────────────────────────

    def _sync_maybe_half_open(self) -> None:
        with self._sync_lock:
            if self._state == CircuitState.OPEN:
                remaining = self._opened_at + self.reset_timeout - time.monotonic()
                if remaining > 0:
                    raise CircuitBreakerOpen(self.name, remaining)
                self._state = CircuitState.HALF_OPEN
                logger.info("Circuit %r → HALF_OPEN (probing recovery)", self.name)

    def _sync_on_success(self) -> None:
        with self._sync_lock:
            if self._state == CircuitState.HALF_OPEN:
                logger.info("Circuit %r → CLOSED (probe succeeded)", self.name)
            self._state = CircuitState.CLOSED
            self._failures = 0

    def _sync_on_failure(self, exc: Exception) -> None:
        with self._sync_lock:
            self._failures += 1
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
                logger.warning("Circuit %r → OPEN (probe failed: %s)", self.name, exc)
            elif self._failures >= self.fail_max:
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()
                logger.warning(
                    "Circuit %r → OPEN (%d/%d failures: %s)",
                    self.name, self._failures, self.fail_max, exc,
                )


# ── Global registry ───────────────────────────────────────────────────────────

_REGISTRY: dict[str, HyperCircuitBreaker] = {}


def get_breaker(name: str, fail_max: int = 5, reset_timeout: int = 30) -> HyperCircuitBreaker:
    """Get-or-create a named circuit breaker from the global registry."""
    if name not in _REGISTRY:
        _REGISTRY[name] = HyperCircuitBreaker(name, fail_max=fail_max, reset_timeout=reset_timeout)
    return _REGISTRY[name]


def all_breakers() -> list[dict]:
    """Snapshot of all registered breakers — safe to include in health responses."""
    return [b.as_dict() for b in _REGISTRY.values()]
