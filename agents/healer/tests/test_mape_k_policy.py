"""Restart-policy tests for the MAPE-K engine (agents/healer/mape_k_engine.py).

Regression context (2026-10-13 log analysis): in 2.5 days the healer did 34 docker restarts, logged ZERO recoveries and
29 "still unhealthy after heal", because it judged a restart after one 5 s probe while hypercode-core needs ~90-230 s
to boot; the failed-heal counters reached 32/18 and never reset; and a single slow probe under host load was enough
to trigger a restart.
"""
from __future__ import annotations

import asyncio
import sys
import time
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import mape_k_engine as eng  # noqa: E402
from mape_k_engine import (  # noqa: E402
    HealAction,
    KnowledgeBase,
    ServiceConfig,
    ServiceStatus,
    analyze,
    execute,
    maybe_reset_backoff,
    plan,
    schedule_heal,
)

H, D, C = ServiceStatus.HEALTHY, ServiceStatus.DEGRADED, ServiceStatus.CRITICAL


def make_service(**kw) -> ServiceConfig:
    svc = ServiceConfig("Svc", 8000, "http://svc:8000/health", "svc", **kw)
    # a stable baseline (~100 ms +/- 5) so a 5000 ms probe has a huge Z-score
    for i in range(30):
        svc.history.append((time.time(), H, 100.0 + (i % 3) * 5))
    return svc


# ------------------------------------------------------------------ analyze: needs consecutive bad probes
def test_single_critical_probe_does_not_restart():
    svc, kb = make_service(), KnowledgeBase()
    anomaly, _reason, _z = analyze(svc, C, 5000.0, kb)
    assert anomaly is False


def test_single_latency_outlier_with_5xx_does_not_restart():
    """Old rule: status != HEALTHY and Z > 3 was enough, i.e. ONE slow 5xx restarted the service."""
    svc, kb = make_service(), KnowledgeBase()
    anomaly, _reason, z = analyze(svc, D, 4000.0, kb)
    assert z > 3.0
    assert anomaly is False


def test_three_consecutive_critical_probes_restart():
    svc, kb = make_service(), KnowledgeBase()
    results = [analyze(svc, C, 5000.0, kb)[0] for _ in range(3)]
    assert results == [False, False, True]


def test_degraded_streak_triggers_after_three():
    """The old DEGRADED branch was dead code: consecutive_failures was reset for every non-CRITICAL status."""
    svc, kb = make_service(), KnowledgeBase()
    results = [analyze(svc, D, 120.0, kb)[0] for _ in range(3)]
    assert results == [False, False, True]


def test_persistent_latency_outlier_restarts_after_three():
    svc, kb = make_service(), KnowledgeBase()
    outcomes = [analyze(svc, D, 4000.0, kb) for _ in range(3)]
    assert [o[0] for o in outcomes] == [False, False, True]


def test_healthy_probe_resets_the_streaks():
    svc, kb = make_service(), KnowledgeBase()
    analyze(svc, C, 5000.0, kb)
    analyze(svc, C, 5000.0, kb)
    analyze(svc, H, 100.0, kb)
    assert svc.consecutive_unhealthy == 0 and svc.consecutive_failures == 0
    assert analyze(svc, C, 5000.0, kb)[0] is False  # streak restarted from 1


def test_min_consecutive_is_configurable(monkeypatch):
    monkeypatch.setattr(eng, "HEALER_RESTART_MIN_CONSECUTIVE", 1)
    svc, kb = make_service(), KnowledgeBase()
    assert analyze(svc, C, 5000.0, kb)[0] is True


# ------------------------------------------------------------------ plan
def test_plan_skips_while_a_heal_is_in_flight():
    svc, kb = make_service(), KnowledgeBase()
    svc.healing = True
    assert plan(svc, C, "x", kb) == HealAction.NO_ACTION


def test_plan_restarts_critical_service_and_only_alerts_for_non_critical():
    kb = KnowledgeBase()
    assert plan(make_service(), C, "x", kb) == HealAction.DOCKER_RESTART
    assert plan(make_service(critical=False), C, "x", kb) == HealAction.ALERT_ONLY


def test_dashboard_is_alert_only_and_core_gets_a_long_startup_grace():
    by_name = {s.name: s for s in eng.DEFAULT_SERVICES}
    assert by_name["Mission Control"].critical is False
    assert by_name["HyperCode Backend"].startup_grace_seconds >= 180
    assert by_name["HyperCode Backend"].probe_timeout > 5.0


# ------------------------------------------------------------------ execute: grace-period verification
class _FakeDocker:
    restarted: list[str] = []

    class DockerClient:
        @staticmethod
        def from_env():
            class _Containers:
                @staticmethod
                def get(name):
                    class _C:
                        @staticmethod
                        def restart():
                            _FakeDocker.restarted.append(name)
                    return _C
            return types.SimpleNamespace(containers=_Containers)


@pytest.fixture(autouse=True)
def _fakes(monkeypatch):
    _FakeDocker.restarted = []
    monkeypatch.setattr(eng, "docker_sdk", _FakeDocker)
    monkeypatch.setattr(eng, "_DOCKER_AVAILABLE", True)
    monkeypatch.setattr(eng, "HEALER_VERIFY_POLL_SECONDS", 0.0)
    fake_core = types.ModuleType("core_events")

    async def _publish(*_a, **_k):  # never touch the network from tests
        return None

    fake_core.publish_core_event = _publish
    monkeypatch.setitem(sys.modules, "core_events", fake_core)


def _script_monitor(monkeypatch, statuses):
    seq = iter(statuses)

    async def fake_monitor(_svc):
        return next(seq, C), 10.0

    monkeypatch.setattr(eng, "monitor", fake_monitor)


async def test_slow_booting_service_is_recorded_as_recovered(monkeypatch):
    """core boots in ~90 s: the old single 5 s probe always failed it. Now it polls within the grace period."""
    svc, kb = make_service(startup_grace_seconds=30.0), KnowledgeBase()
    _script_monitor(monkeypatch, [C, C, C, H])
    event = await execute(svc, HealAction.DOCKER_RESTART, "t", kb)
    assert _FakeDocker.restarted == ["svc"]
    assert event.success is True
    assert event.mttr_seconds is not None
    assert svc.consecutive_failed_heals == 0 and svc.backoff_until is None


async def test_service_that_never_recovers_is_a_failed_heal_after_the_grace_period(monkeypatch):
    svc, kb = make_service(startup_grace_seconds=0.05), KnowledgeBase()
    _script_monitor(monkeypatch, [])  # always CRITICAL
    event = await execute(svc, HealAction.DOCKER_RESTART, "t", kb)
    assert event.success is False
    assert svc.consecutive_failed_heals == 1


# ------------------------------------------------------------------ backoff reset
def test_backoff_resets_after_sustained_health():
    svc = make_service()
    svc.consecutive_failed_heals = 32
    svc.backoff_until = time.time() + 1800
    svc.healthy_streak = eng.HEALER_RESET_AFTER_HEALTHY - 1
    assert maybe_reset_backoff(svc) is False
    svc.healthy_streak = eng.HEALER_RESET_AFTER_HEALTHY
    assert maybe_reset_backoff(svc) is True
    assert svc.consecutive_failed_heals == 0 and svc.backoff_until is None


def test_backoff_not_reset_while_a_heal_is_in_flight():
    svc = make_service()
    svc.consecutive_failed_heals = 5
    svc.healthy_streak = 99
    svc.healing = True
    assert maybe_reset_backoff(svc) is False


# ------------------------------------------------------------------ scheduling: verifying one service must not block others
async def test_schedule_heal_returns_immediately_and_clears_healing(monkeypatch):
    started, release = asyncio.Event(), asyncio.Event()

    async def slow_execute(_svc, _action, _reason, _kb):
        started.set()
        await release.wait()

    monkeypatch.setattr(eng, "execute", slow_execute)
    svc, kb = make_service(), KnowledgeBase()
    t0 = time.monotonic()
    task = schedule_heal(svc, HealAction.DOCKER_RESTART, "t", kb)
    assert time.monotonic() - t0 < 0.1
    assert svc.healing is True
    await asyncio.wait_for(started.wait(), 1)
    assert plan(svc, C, "x", kb) == HealAction.NO_ACTION  # no second heal while verifying
    release.set()
    await asyncio.wait_for(task, 1)
    assert svc.healing is False


async def test_heal_failure_still_clears_healing(monkeypatch):
    async def boom(*_a, **_k):
        raise RuntimeError("docker gone")

    monkeypatch.setattr(eng, "execute", boom)
    svc = make_service()
    await schedule_heal(svc, HealAction.DOCKER_RESTART, "t", KnowledgeBase())
    assert svc.healing is False


async def test_loop_keeps_probing_other_services_while_one_is_healing(monkeypatch):
    slow = make_service()
    slow.name = "Slow"
    other = make_service()
    other.name = "Other"
    probes: dict[str, int] = {"Slow": 0, "Other": 0}

    async def fake_monitor(svc):
        probes[svc.name] += 1
        return (C, 5000.0) if svc.name == "Slow" else (H, 100.0)

    release = asyncio.Event()

    async def slow_execute(svc, action, reason, kb):
        await release.wait()

    monkeypatch.setattr(eng, "monitor", fake_monitor)
    monkeypatch.setattr(eng, "execute", slow_execute)
    monkeypatch.setattr(eng, "HEALER_RESTART_MIN_CONSECUTIVE", 1)
    loop_task = asyncio.create_task(eng.mape_k_loop([slow, other], KnowledgeBase(), interval_seconds=0.02))
    await asyncio.sleep(0.4)
    release.set()
    loop_task.cancel()
    try:
        await loop_task
    except asyncio.CancelledError:
        pass
    # Other was probed many times even though Slow's heal was "running" the whole time
    assert probes["Other"] >= 5
    assert slow.healing is False or probes["Slow"] >= 1

# ------------------------------------------------------------------ logging: the success path must be visible
import io  # noqa: E402
import logging  # noqa: E402


def _capture_handler():
    buf = io.StringIO()
    h = logging.StreamHandler(buf)
    h.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    return h, buf


@pytest.fixture
def _restore_mape_logger():
    lg = eng.logger
    saved = (lg.level, list(lg.handlers), lg.propagate)
    yield lg
    lg.setLevel(saved[0])
    lg.handlers[:] = saved[1]
    lg.propagate = saved[2]


def test_configure_logging_emits_info_that_was_previously_dropped(_restore_mape_logger):
    """Before: the 'mape_k' logger had no handler, so only WARNING+ reached docker logs (via the last-resort handler)."""
    lg = _restore_mape_logger
    lg.handlers.clear()
    h, buf = _capture_handler()
    eng.configure_logging(h)
    lg.info("[EXECUTE] Svc recovered in 4.2s")
    lg.debug("[PLAN] Svc -- cooldown active, skipping heal")
    out = buf.getvalue()
    assert "INFO [EXECUTE] Svc recovered in 4.2s" in out
    assert "cooldown active" not in out  # DEBUG noise stays off at the default level
    assert lg.propagate is False


def test_configure_logging_is_idempotent_and_level_overridable(_restore_mape_logger):
    lg = _restore_mape_logger
    lg.handlers.clear()
    h, buf = _capture_handler()
    eng.configure_logging(h)
    eng.configure_logging(h)
    assert lg.handlers.count(h) == 1
    eng.configure_logging(h, level="WARNING")
    lg.info("quiet")
    lg.warning("loud")
    assert "quiet" not in buf.getvalue() and "loud" in buf.getvalue()


async def test_recovery_is_logged_when_a_restart_succeeds(monkeypatch, caplog):
    caplog.set_level(logging.INFO, logger="mape_k")
    svc, kb = make_service(startup_grace_seconds=30.0), KnowledgeBase()
    _script_monitor(monkeypatch, [C, H])
    await execute(svc, HealAction.DOCKER_RESTART, "t", kb)
    assert "recovered in" in caplog.text
    assert "Docker restart sent" in caplog.text


def test_plan_skip_notices_are_debug_not_info(caplog):
    caplog.set_level(logging.INFO, logger="mape_k")
    svc, kb = make_service(), KnowledgeBase()
    svc.healing = True
    plan(svc, C, "x", kb)
    svc.healing = False
    svc.last_healed = time.time()
    plan(svc, C, "x", kb)
    svc.last_healed = None
    svc.backoff_until = time.time() + 60
    plan(svc, C, "x", kb)
    assert "skipping" not in caplog.text
