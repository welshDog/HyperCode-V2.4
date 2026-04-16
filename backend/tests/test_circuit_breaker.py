"""
Gordon Tier 2 Step 4 — Circuit breaker tests.

Tests state transitions: CLOSED → OPEN → HALF_OPEN → CLOSED.
No external dependencies needed.
"""
import asyncio
import time
import pytest

from app.core.circuit_breaker import (
    HyperCircuitBreaker,
    CircuitState,
    CircuitBreakerOpen,
    get_breaker,
    all_breakers,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _ok() -> str:
    return "ok"


async def _fail() -> None:
    raise RuntimeError("simulated failure")


def _ok_sync() -> str:
    return "ok"


def _fail_sync() -> None:
    raise RuntimeError("simulated failure")


# ── Unit tests ────────────────────────────────────────────────────────────────

class TestCircuitBreakerStates:

    @pytest.mark.asyncio
    async def test_starts_closed(self):
        cb = HyperCircuitBreaker("test-closed", fail_max=3, reset_timeout=10)
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_closed_passes_successful_calls(self):
        cb = HyperCircuitBreaker("test-pass", fail_max=3, reset_timeout=10)
        result = await cb.call(_ok)
        assert result == "ok"
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_opens_after_fail_max_failures(self):
        cb = HyperCircuitBreaker("test-open", fail_max=3, reset_timeout=10)
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await cb.call(_fail)
        assert cb.state == CircuitState.OPEN
        assert cb.failure_count == 3

    @pytest.mark.asyncio
    async def test_open_rejects_calls_immediately(self):
        cb = HyperCircuitBreaker("test-reject", fail_max=2, reset_timeout=60)
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(_fail)
        assert cb.state == CircuitState.OPEN
        # Next call should raise CircuitBreakerOpen, NOT RuntimeError
        with pytest.raises(CircuitBreakerOpen) as exc_info:
            await cb.call(_ok)
        assert exc_info.value.name == "test-reject"
        assert exc_info.value.reset_in > 0

    @pytest.mark.asyncio
    async def test_half_open_after_timeout(self):
        cb = HyperCircuitBreaker("test-half-open", fail_max=2, reset_timeout=0)
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(_fail)
        assert cb.state == CircuitState.OPEN
        # reset_timeout=0 means it transitions immediately
        result = await cb.call(_ok)
        assert result == "ok"
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_back_to_open_on_failure(self):
        cb = HyperCircuitBreaker("test-half-fail", fail_max=2, reset_timeout=0)
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(_fail)
        # Timeout elapsed (reset_timeout=0) → probe allowed
        with pytest.raises(RuntimeError):
            await cb.call(_fail)
        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_success_resets_failure_count(self):
        cb = HyperCircuitBreaker("test-reset", fail_max=5, reset_timeout=10)
        for _ in range(3):
            with pytest.raises(RuntimeError):
                await cb.call(_fail)
        assert cb.failure_count == 3
        await cb.call(_ok)
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED


class TestSyncCircuitBreaker:

    def test_sync_closed_passes_calls(self):
        cb = HyperCircuitBreaker("test-sync-pass", fail_max=3, reset_timeout=10)
        result = cb.call_sync(_ok_sync)
        assert result == "ok"

    def test_sync_opens_after_fail_max(self):
        cb = HyperCircuitBreaker("test-sync-open", fail_max=2, reset_timeout=60)
        for _ in range(2):
            with pytest.raises(RuntimeError):
                cb.call_sync(_fail_sync)
        assert cb.state == CircuitState.OPEN

    def test_sync_open_raises_circuit_breaker_open(self):
        cb = HyperCircuitBreaker("test-sync-reject", fail_max=2, reset_timeout=60)
        for _ in range(2):
            with pytest.raises(RuntimeError):
                cb.call_sync(_fail_sync)
        with pytest.raises(CircuitBreakerOpen):
            cb.call_sync(_ok_sync)


class TestRegistry:

    def test_get_breaker_returns_same_instance(self):
        b1 = get_breaker("registry-test", fail_max=3, reset_timeout=10)
        b2 = get_breaker("registry-test")
        assert b1 is b2

    def test_all_breakers_includes_registered(self):
        get_breaker("health-check-breaker", fail_max=5, reset_timeout=30)
        snapshots = all_breakers()
        names = [s["name"] for s in snapshots]
        assert "health-check-breaker" in names

    def test_as_dict_has_required_fields(self):
        cb = HyperCircuitBreaker("test-dict", fail_max=5, reset_timeout=30)
        d = cb.as_dict()
        assert d["name"] == "test-dict"
        assert d["state"] == "closed"
        assert d["failures"] == 0
        assert d["fail_max"] == 5
        assert d["reset_timeout_s"] == 30
        assert d["reset_in_s"] == 0


class TestNamedBreakers:
    """Confirm the three production breakers are registered with correct config."""

    def test_llm_router_breaker_registered(self):
        # Import the module to trigger registration
        import app.core.model_routes  # noqa
        b = get_breaker("llm-router")
        assert b.fail_max == 3
        assert b.reset_timeout == 30

    def test_crew_orchestrator_breaker_registered(self):
        import app.ws.uplink  # noqa
        b = get_breaker("crew-orchestrator")
        assert b.fail_max == 3
        assert b.reset_timeout == 15

    def test_stripe_api_breaker_registered(self):
        import app.services.stripe_service  # noqa
        b = get_breaker("stripe-api")
        assert b.fail_max == 5
        assert b.reset_timeout == 60
