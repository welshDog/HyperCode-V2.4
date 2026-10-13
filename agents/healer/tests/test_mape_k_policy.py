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

# ------------------------------------------------------------------ host-load guard
from mape_k_engine import GuardDecision, HostLoad, evaluate_guard, read_host_load  # noqa: E402

CALM = HostLoad(loadavg1=0.5, ncpu=4, cpu_pressure10=5.0, mem_available_mb=1500.0)
BUSY = HostLoad(loadavg1=12.0, ncpu=4, cpu_pressure10=75.0, mem_available_mb=1500.0)


@pytest.fixture(autouse=True)
def _calm_host_by_default(monkeypatch):
    """Tests must not depend on the load of the machine running them."""
    monkeypatch.setattr(eng, "read_host_load", lambda *a, **k: CALM)


def _write_proc(root: Path, load="0.50 0.60 0.70 1/100 1", psi="some avg10=5.00 avg60=4.00 avg300=3.00 total=1", mem="MemAvailable:    1536000 kB"):
    (root / "pressure").mkdir(parents=True, exist_ok=True)
    if load is not None:
        (root / "loadavg").write_text(load)
    if psi is not None:
        (root / "pressure" / "cpu").write_text(psi + "\n")
    if mem is not None:
        (root / "meminfo").write_text("MemTotal: 4000000 kB\n" + mem + "\n")


def test_read_host_load_parses_proc_files(tmp_path):
    _write_proc(tmp_path, load="12.34 8.00 5.00 3/100 9", psi="some avg10=73.28 avg60=60.43 avg300=42.36 total=1", mem="MemAvailable:    1048576 kB")
    h = read_host_load(str(tmp_path))
    assert h.loadavg1 == pytest.approx(12.34)
    assert h.cpu_pressure10 == pytest.approx(73.28)
    assert h.mem_available_mb == pytest.approx(1024.0)
    assert h.ncpu >= 1


def test_read_host_load_leaves_unreadable_signals_none(tmp_path):
    h = read_host_load(str(tmp_path / "does-not-exist"))
    assert h.loadavg1 is None and h.cpu_pressure10 is None and h.mem_available_mb is None
    _write_proc(tmp_path, load="garbage", psi=None, mem=None)
    h = read_host_load(str(tmp_path))
    assert h.loadavg1 is None and h.cpu_pressure10 is None


def test_calm_host_does_not_hold():
    assert evaluate_guard([make_service()], CALM) == GuardDecision(False, "")


def test_high_cpu_pressure_holds():
    d = evaluate_guard([make_service()], HostLoad(loadavg1=1.0, ncpu=4, cpu_pressure10=60.0, mem_available_mb=1500.0))
    assert d.hold and "CPU pressure 60%" in d.reason


def test_high_load_per_cpu_holds():
    d = evaluate_guard([make_service()], HostLoad(loadavg1=9.0, ncpu=4, cpu_pressure10=5.0, mem_available_mb=1500.0))
    assert d.hold and "load 9.0 on 4 CPUs" in d.reason


def test_low_memory_signal_is_off_by_default_and_works_when_enabled(monkeypatch):
    low = HostLoad(loadavg1=0.5, ncpu=4, cpu_pressure10=5.0, mem_available_mb=900.0)
    assert evaluate_guard([make_service()], low).hold is False
    monkeypatch.setattr(eng, "HEALER_LOAD_GUARD_MIN_MEM_MB", 1000.0)
    d = evaluate_guard([make_service()], low)
    assert d.hold and "900 MB" in d.reason


def test_unreadable_load_fails_open():
    assert evaluate_guard([make_service()], HostLoad()).hold is False


def test_guard_can_be_disabled(monkeypatch):
    monkeypatch.setattr(eng, "HEALER_LOAD_GUARD_ENABLED", False)
    assert evaluate_guard([make_service()], BUSY).hold is False


def _recently_healthy_but_down(name, age=30.0):
    s = make_service()
    s.name = name
    s.last_status = C
    s.last_healthy_at = time.time() - age
    return s


def test_two_services_newly_unhealthy_at_once_is_systemic():
    d = evaluate_guard([_recently_healthy_but_down("A"), _recently_healthy_but_down("B")], CALM)
    assert d.hold and "2 services went unhealthy at once" in d.reason


def test_a_single_unhealthy_service_is_not_systemic():
    assert evaluate_guard([_recently_healthy_but_down("A"), make_service()], CALM).hold is False


def test_services_down_for_days_are_not_counted():
    """The stopped observability stack must not make every real failure look systemic."""
    stopped = [make_service() for _ in range(3)]
    for s in stopped:
        s.last_status = C
        s.last_healthy_at = None
    assert evaluate_guard([*stopped, _recently_healthy_but_down("A")], CALM).hold is False
    old = _recently_healthy_but_down("B", age=eng.HEALER_LOAD_GUARD_RECENT_HEALTHY_SECONDS + 60)
    assert evaluate_guard([old, _recently_healthy_but_down("A")], CALM).hold is False


# ------------------------------------------------------------------ guard in plan()
HOLD = GuardDecision(hold=True, reason="CPU pressure 75% >= 50%")


def test_restart_is_held_while_guard_is_active():
    svc, kb = make_service(), KnowledgeBase()
    assert plan(svc, C, "x", kb, HOLD) == HealAction.NO_ACTION
    assert svc.guard_since is not None


def test_restart_is_allowed_when_guard_is_inactive_or_absent():
    kb = KnowledgeBase()
    assert plan(make_service(), C, "x", kb, GuardDecision()) == HealAction.DOCKER_RESTART
    assert plan(make_service(), C, "x", kb) == HealAction.DOCKER_RESTART


def test_alert_only_is_never_held():
    assert plan(make_service(critical=False), C, "x", KnowledgeBase(), HOLD) == HealAction.ALERT_ONLY


def test_http_restart_is_held_too():
    svc = make_service()
    svc.restart_url = "http://svc/restart"
    assert plan(svc, C, "x", KnowledgeBase(), HOLD) == HealAction.NO_ACTION


def test_held_restart_is_released_once_the_guard_clears():
    svc, kb = make_service(), KnowledgeBase()
    plan(svc, C, "x", kb, HOLD)
    assert plan(svc, C, "x", kb, GuardDecision()) == HealAction.DOCKER_RESTART
    assert svc.guard_since is None


def test_a_service_held_too_long_is_restarted_anyway(monkeypatch):
    """A real outage under sustained load must still get fixed."""
    svc, kb = make_service(), KnowledgeBase()
    monkeypatch.setattr(eng, "HEALER_LOAD_GUARD_MAX_HOLD_SECONDS", 600.0)
    plan(svc, C, "x", kb, HOLD)
    svc.guard_since = time.time() - 601
    assert plan(svc, C, "x", kb, HOLD) == HealAction.DOCKER_RESTART


def test_hold_is_logged_once_not_every_cycle(caplog):
    caplog.set_level(logging.WARNING, logger="mape_k")
    svc, kb = make_service(), KnowledgeBase()
    for _ in range(5):
        plan(svc, C, "x", kb, HOLD)
    assert caplog.text.count("restart HELD") == 1


def test_healthy_probe_clears_a_pending_hold_and_records_the_time():
    svc, kb = make_service(), KnowledgeBase()
    svc.guard_since = time.time() - 30
    analyze(svc, H, 100.0, kb)
    assert svc.guard_since is None
    assert svc.last_healthy_at is not None and time.time() - svc.last_healthy_at < 5


# ------------------------------------------------------------------ guard in the loop
async def test_loop_holds_restarts_under_load_then_releases(monkeypatch):
    svc = make_service()
    svc.name = "Down"
    started: list[str] = []
    state = {"load": BUSY}

    async def fake_monitor(_s):
        return C, 5000.0

    def fake_schedule(service, action, reason, kb):
        started.append(service.name)
        service.healing = False

    monkeypatch.setattr(eng, "monitor", fake_monitor)
    monkeypatch.setattr(eng, "schedule_heal", fake_schedule)
    monkeypatch.setattr(eng, "read_host_load", lambda *a, **k: state["load"])
    monkeypatch.setattr(eng, "HEALER_RESTART_MIN_CONSECUTIVE", 1)
    monkeypatch.setattr(eng, "HEALER_COOLDOWN_SECONDS", 0)
    loop_task = asyncio.create_task(eng.mape_k_loop([svc], KnowledgeBase(), interval_seconds=0.02))
    await asyncio.sleep(0.3)
    held_restarts = len(started)
    state["load"] = CALM
    await asyncio.sleep(0.3)
    loop_task.cancel()
    try:
        await loop_task
    except asyncio.CancelledError:
        pass
    assert held_restarts == 0           # nothing restarted while the host was busy
    assert len(started) >= 1            # restarted once the guard cleared
    assert svc.guard_since is None

# ------------------------------------------------------------------ alert_only: one notice per outage, not one per minute
def test_alert_only_service_alerts_once_per_outage():
    svc, kb = make_service(critical=False), KnowledgeBase()
    assert plan(svc, C, "x", kb) == HealAction.ALERT_ONLY
    for _ in range(20):
        assert plan(svc, C, "x", kb) == HealAction.NO_ACTION


def test_alert_repeats_after_the_repeat_interval(monkeypatch):
    monkeypatch.setattr(eng, "HEALER_ALERT_REPEAT_SECONDS", 3600.0)
    svc, kb = make_service(critical=False), KnowledgeBase()
    plan(svc, C, "x", kb)
    svc.last_alerted_at = time.time() - 3601
    assert plan(svc, C, "x", kb) == HealAction.ALERT_ONLY


def test_repeat_interval_zero_restores_the_old_alert_every_cycle(monkeypatch):
    monkeypatch.setattr(eng, "HEALER_ALERT_REPEAT_SECONDS", 0.0)
    svc, kb = make_service(critical=False), KnowledgeBase()
    assert [plan(svc, C, "x", kb) for _ in range(3)] == [HealAction.ALERT_ONLY] * 3


def test_recovery_logs_once_and_rearms_the_alert(caplog):
    caplog.set_level(logging.INFO, logger="mape_k")
    svc, kb = make_service(critical=False), KnowledgeBase()
    plan(svc, C, "x", kb)
    assert plan(svc, C, "x", kb) == HealAction.NO_ACTION
    analyze(svc, H, 100.0, kb)
    assert "[ALERT] Svc recovered" in caplog.text
    assert svc.last_alerted_at is None and svc.anomaly_logged is False
    assert plan(svc, C, "x", kb) == HealAction.ALERT_ONLY  # a new outage alerts again


def test_service_that_was_never_alerted_logs_no_recovery(caplog):
    caplog.set_level(logging.INFO, logger="mape_k")
    svc, kb = make_service(), KnowledgeBase()
    analyze(svc, H, 100.0, kb)
    assert "recovered" not in caplog.text


def test_critical_services_are_not_rate_limited_by_the_alert_logic():
    svc, kb = make_service(), KnowledgeBase()
    assert plan(svc, C, "x", kb) == HealAction.DOCKER_RESTART
    svc.last_healed = None
    assert plan(svc, C, "x", kb) == HealAction.DOCKER_RESTART


async def test_loop_alerts_once_and_logs_the_anomaly_once_for_a_long_outage(monkeypatch, caplog):
    """The regression: a stopped alert-only service used to produce an ANALYZE warning every cycle and an alert every cooldown."""
    caplog.set_level(logging.WARNING, logger="mape_k")
    svc = make_service(critical=False)
    svc.name = "Stopped"
    alerts: list[str] = []

    async def fake_monitor(_s):
        return C, 5000.0

    def fake_schedule(service, action, reason, kb):
        alerts.append(action.value)
        service.healing = False

    monkeypatch.setattr(eng, "monitor", fake_monitor)
    monkeypatch.setattr(eng, "schedule_heal", fake_schedule)
    monkeypatch.setattr(eng, "HEALER_RESTART_MIN_CONSECUTIVE", 1)
    monkeypatch.setattr(eng, "HEALER_COOLDOWN_SECONDS", 0)
    loop_task = asyncio.create_task(eng.mape_k_loop([svc], KnowledgeBase(), interval_seconds=0.01))
    await asyncio.sleep(0.4)  # dozens of cycles
    loop_task.cancel()
    try:
        await loop_task
    except asyncio.CancelledError:
        pass
    assert alerts == ["alert_only"]
    assert caplog.text.count("anomaly detected") == 1

# ------------------------------------------------------------------ concurrent probing
def _named(n, **kw):
    svc = make_service(**kw)
    svc.name = n
    return svc


async def _run_loop_for(seconds, services, **kw):
    task = asyncio.create_task(eng.mape_k_loop(services, KnowledgeBase(), interval_seconds=kw.get("interval", 10)))
    await asyncio.sleep(seconds)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def test_services_are_probed_concurrently(monkeypatch):
    """Sequential probing made a cycle the SUM of every probe (13.8 s for 3 stopped services on this stack)."""
    inflight = {"now": 0, "max": 0}

    async def slow_monitor(_s):
        inflight["now"] += 1
        inflight["max"] = max(inflight["max"], inflight["now"])
        await asyncio.sleep(0.1)
        inflight["now"] -= 1
        return H, 100.0

    monkeypatch.setattr(eng, "monitor", slow_monitor)
    services = [_named(f"S{i}") for i in range(5)]
    t0 = time.monotonic()
    await _run_loop_for(0.25, services)
    assert inflight["max"] == 5
    assert time.monotonic() - t0 < 0.5


async def test_probe_concurrency_of_one_restores_sequential_probing(monkeypatch):
    inflight = {"now": 0, "max": 0}

    async def slow_monitor(_s):
        inflight["now"] += 1
        inflight["max"] = max(inflight["max"], inflight["now"])
        await asyncio.sleep(0.02)
        inflight["now"] -= 1
        return H, 100.0

    monkeypatch.setattr(eng, "monitor", slow_monitor)
    monkeypatch.setattr(eng, "HEALER_PROBE_CONCURRENCY", 1)
    await _run_loop_for(0.2, [_named(f"S{i}") for i in range(4)])
    assert inflight["max"] == 1


async def test_a_hung_probe_does_not_delay_another_services_heal(monkeypatch):
    """A slow service must not hold up the decision about a failing one (it did: probes ran one after another)."""
    scheduled: dict[str, float] = {}
    t0 = time.monotonic()

    async def fake_monitor(svc):
        if svc.name == "Hung":
            await asyncio.sleep(0.6)
            return H, 100.0
        return C, 5000.0

    def fake_schedule(service, action, reason, kb):
        scheduled.setdefault(service.name, time.monotonic() - t0)
        service.healing = False

    monkeypatch.setattr(eng, "monitor", fake_monitor)
    monkeypatch.setattr(eng, "schedule_heal", fake_schedule)
    monkeypatch.setattr(eng, "HEALER_RESTART_MIN_CONSECUTIVE", 1)
    monkeypatch.setattr(eng, "HEALER_COOLDOWN_SECONDS", 0)
    await _run_loop_for(0.4, [_named("Hung"), _named("Failing")])
    assert "Failing" in scheduled and scheduled["Failing"] < 0.2


async def test_an_error_in_one_service_does_not_stop_the_others(monkeypatch, caplog):
    caplog.set_level(logging.ERROR, logger="mape_k")
    probed: set[str] = set()

    async def fake_monitor(svc):
        probed.add(svc.name)
        if svc.name == "Broken":
            raise RuntimeError("boom")
        return H, 100.0

    monkeypatch.setattr(eng, "monitor", fake_monitor)
    await _run_loop_for(0.15, [_named("Broken"), _named("Fine")])
    assert probed == {"Broken", "Fine"}
    assert "Error processing Broken: boom" in caplog.text
