"""
MAPE-K ENGINE -- HyperCode V2.0 Self-Healing Brain
---------------------------------------------------
Loop: Monitor -> Analyze -> Plan -> Execute
Phase 1: Reactive healing with Z-score anomaly detection
Phase 2: Predictive healing (Isolation Forest) -- coming soon

Built by @welshDog -- HyperFocus Zone, Llanelli, Wales
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import statistics
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

# Backoff config — tuneable via env vars
HEALER_MAX_RESTART_ATTEMPTS: int = int(os.getenv("HEALER_MAX_RESTART_ATTEMPTS", "3"))
HEALER_BACKOFF_BASE_SECONDS: int = int(os.getenv("HEALER_BACKOFF_BASE_SECONDS", "300"))   # 5 min base
HEALER_MAX_BACKOFF_SECONDS:  int = int(os.getenv("HEALER_MAX_BACKOFF_SECONDS",  "1800"))  # 30 min cap

# Restart policy -- tuneable via env vars.
# A restart needs this many CONSECUTIVE bad probes (one slow/failed probe under host load must not restart a
# service: restarting hypercode-core costs ~90 s of downtime on this host, the dashboard's last restart broke its rootfs).
HEALER_RESTART_MIN_CONSECUTIVE: int = int(os.getenv("HEALER_RESTART_MIN_CONSECUTIVE", "3"))
# After a restart, poll this often (up to the service's startup_grace_seconds) before deciding the heal failed.
HEALER_VERIFY_POLL_SECONDS: float = float(os.getenv("HEALER_VERIFY_POLL_SECONDS", "5"))
# This many consecutive HEALTHY probes (~1 min at the default 10 s loop) clear the failed-heal counter and backoff,
# so a service that recovered on its own is not stuck at the maximum backoff forever.
HEALER_RESET_AFTER_HEALTHY: int = int(os.getenv("HEALER_RESET_AFTER_HEALTHY", "6"))
HEALER_COOLDOWN_SECONDS: int = int(os.getenv("HEALER_COOLDOWN_SECONDS", "60"))
# Alert-only services (critical=False, e.g. the observability stack that is deliberately stopped) alert ONCE per outage, then
# repeat at most this often. Before this, each such service raised ~1 alert/min (WARNING lines + an event published to core)
# for as long as it stayed down. 0 = alert on every cooldown cycle (the old behaviour).
HEALER_ALERT_REPEAT_SECONDS: float = float(os.getenv("HEALER_ALERT_REPEAT_SECONDS", "3600"))

# Services are probed concurrently (up to this many at once). Probing them one after another made a cycle the SUM of all probe
# times: on this stack three stopped services cost ~4 s each (the hostname lookup fails slowly), so a cycle took ~13.8 s against a
# 10 s interval, delayed every other service's check, and stretched "3 consecutive failures" to ~40 s. 1 = sequential (old behaviour).
HEALER_PROBE_CONCURRENCY: int = int(os.getenv("HEALER_PROBE_CONCURRENCY", "16"))

# Host-load guard -- tuneable via env vars. Restarting a service while the VM is starved makes things worse (core costs
# ~90 s of downtime per restart; the dashboard's last restart under build load broke its rootfs), and probe failures
# during a spike are usually the load, not the service. While the guard is active, docker/http restarts are HELD
# (alert-only actions are never held). It fails open: if the load cannot be read, nothing is held.
HEALER_LOAD_GUARD_ENABLED: bool = os.getenv("HEALER_LOAD_GUARD_ENABLED", "true").strip().lower() not in ("0", "false", "no", "off")
HEALER_LOAD_GUARD_CPU_PRESSURE: float = float(os.getenv("HEALER_LOAD_GUARD_CPU_PRESSURE", "50"))      # PSI "some" avg10, percent
HEALER_LOAD_GUARD_LOAD_PER_CPU: float = float(os.getenv("HEALER_LOAD_GUARD_LOAD_PER_CPU", "2.0"))     # 1-min loadavg / CPUs
HEALER_LOAD_GUARD_MIN_MEM_MB: float = float(os.getenv("HEALER_LOAD_GUARD_MIN_MEM_MB", "0"))          # 0 = off
HEALER_LOAD_GUARD_SYSTEMIC_MIN: int = int(os.getenv("HEALER_LOAD_GUARD_SYSTEMIC_MIN", "2"))          # <2 = off
HEALER_LOAD_GUARD_RECENT_HEALTHY_SECONDS: float = float(os.getenv("HEALER_LOAD_GUARD_RECENT_HEALTHY_SECONDS", "300"))
# A service held this long is restarted anyway: a real outage under sustained load must still get fixed.
HEALER_LOAD_GUARD_MAX_HOLD_SECONDS: float = float(os.getenv("HEALER_LOAD_GUARD_MAX_HOLD_SECONDS", "600"))

import httpx

try:
    import docker as docker_sdk  # type: ignore[import]
    _DOCKER_AVAILABLE = True
except ImportError:
    docker_sdk = None  # type: ignore[assignment]
    _DOCKER_AVAILABLE = False

logger = logging.getLogger("mape_k")


def configure_logging(handler: logging.Handler, level: Optional[str] = None) -> None:
    """Attach `handler` to the "mape_k" logger so its INFO messages are actually emitted.

    main.py only configured the "healer.main" logger. "mape_k" had no handler, so Python's last-resort handler
    printed WARNING and above only: the success path (`recovered in Ns`, `Docker restart sent`, backoff resets) is
    logged at INFO and was therefore invisible in `docker logs`, which made successful heals look like they never
    happened. Level defaults to INFO; override with HEALER_LOG_LEVEL (e.g. DEBUG, WARNING).
    """
    name = (level or os.getenv("HEALER_LOG_LEVEL", "INFO")).upper()
    logger.setLevel(getattr(logging, name, logging.INFO))
    if handler not in logger.handlers:
        logger.addHandler(handler)
    logger.propagate = False  # the handler is attached here; do not also emit via the root logger


# ------------------------------------
# ENUMS
# ------------------------------------

class ServiceStatus(str, Enum):
    """Possible health states for a monitored service."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class HealAction(str, Enum):
    """Available remediation actions the EXECUTE phase can take."""

    HTTP_RESTART = "http_restart"
    DOCKER_RESTART = "docker_restart"
    SCALE_UP = "scale_up"
    ALERT_ONLY = "alert_only"
    NO_ACTION = "no_action"


# ------------------------------------
# DATA MODELS
# ------------------------------------

@dataclass
class ServiceConfig:
    """Configuration and live state for one monitored service."""

    name: str
    port: int
    check_url: str
    compose_name: Optional[str] = None
    restart_url: Optional[str] = None
    critical: bool = True
    probe_timeout: float = 5.0           # seconds a health probe may take before it counts as CRITICAL
    startup_grace_seconds: float = 30.0  # how long a restarted service gets to turn HEALTHY before the heal is "failed"
    history: deque[tuple[float, ServiceStatus, float]] = field(
        default_factory=lambda: deque(maxlen=60)
    )
    last_status: ServiceStatus = ServiceStatus.UNKNOWN
    consecutive_failures: int = 0   # streak of hard failures (probe error/timeout)
    consecutive_unhealthy: int = 0  # streak of any non-HEALTHY probe (hard failure or 5xx)
    healthy_streak: int = 0         # streak of HEALTHY probes
    healing: bool = False           # a restart is in flight / being verified: do not plan another
    last_healthy_at: Optional[float] = None  # last time a probe was HEALTHY (for the 'newly unhealthy' systemic signal)
    guard_since: Optional[float] = None      # when the load guard started holding a restart for this service
    last_alerted_at: Optional[float] = None  # last alert_only notice for the current outage (None = none sent)
    anomaly_logged: bool = False             # the current anomaly episode has already been logged at WARNING
    total_heals: int = 0
    last_healed: Optional[float] = None
    consecutive_failed_heals: int = 0
    backoff_until: Optional[float] = None


@dataclass
class HealEvent:
    """Record of a single healing action and its outcome."""

    timestamp: str
    service: str
    status_before: ServiceStatus
    action_taken: HealAction
    success: bool
    reason: str
    mttr_seconds: Optional[float] = None


# ------------------------------------
# KNOWLEDGE BASE
# ------------------------------------

class KnowledgeBase:
    """The K in MAPE-K. Shared memory across all phases."""

    system_start: float

    def __init__(self) -> None:
        """Initialise empty knowledge base."""
        self.heal_history: list[HealEvent] = []
        self.anomaly_scores: dict[str, float] = {}
        self.action_success_rates: dict[HealAction, list[bool]] = defaultdict(list)
        self.system_start = time.time()

    def record_heal(self, event: HealEvent) -> None:
        """Store a heal event and cap history at 500 entries."""
        self.heal_history.append(event)
        self.action_success_rates[event.action_taken].append(event.success)
        if len(self.heal_history) > 500:
            self.heal_history = self.heal_history[-500:]

    def success_rate(self, action: HealAction) -> float:
        """Return 0.0-1.0 historical success rate for an action."""
        results = self.action_success_rates.get(action, [])
        if not results:
            return 0.0
        return sum(results) / len(results)

    def recent_heals(self, minutes: int = 60) -> list[HealEvent]:
        """Return heal events within the last N minutes."""
        cutoff = time.time() - (minutes * 60)
        cutoff_str = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()
        return [e for e in self.heal_history if e.timestamp >= cutoff_str]

    def stats(self) -> dict[str, object]:
        """Return a summary dict suitable for API responses."""
        recent = self.recent_heals(60)
        successful = [e for e in recent if e.success]
        mttr_values = [
            e.mttr_seconds for e in successful
            if e.mttr_seconds is not None
        ]
        return {
            "total_heals": len(self.heal_history),
            "heals_last_hour": len(recent),
            "auto_fix_success_rate": round(
                len(successful) / len(recent) * 100 if recent else 0, 1
            ),
            "avg_mttr_seconds": (
                round(statistics.mean(mttr_values), 1) if mttr_values else None
            ),
            "uptime_seconds": round(time.time() - self.system_start),
        }


# ------------------------------------
# MONITOR PHASE
# ------------------------------------

async def monitor(service: ServiceConfig) -> tuple[ServiceStatus, float]:
    """Poll a service health endpoint; return (status, response_time_ms)."""
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=service.probe_timeout) as client:
            resp = await client.get(service.check_url)
        elapsed = (time.monotonic() - start) * 1000
        status = ServiceStatus.HEALTHY if resp.status_code < 500 else ServiceStatus.DEGRADED
    except Exception:
        elapsed = (time.monotonic() - start) * 1000
        status = ServiceStatus.CRITICAL

    service.history.append((time.time(), status, elapsed))
    return status, elapsed


# ------------------------------------
# ANALYZE PHASE
# ------------------------------------

def analyze(
    service: ServiceConfig,
    current_status: ServiceStatus,
    response_ms: float,
    kb: KnowledgeBase,
) -> tuple[bool, str, float]:
    """Return (is_anomaly, reason, z_score) using 3-sigma rule."""
    response_times: list[float] = [
        rt for _, _, rt in service.history if rt > 0
    ]
    z_score: float = 0.0
    if len(response_times) >= 10:
        mean_rt: float = statistics.mean(response_times)
        stdev_rt: float = statistics.stdev(response_times)
        if stdev_rt > 0:
            z_score = abs((response_ms - mean_rt) / stdev_rt)

    kb.anomaly_scores[service.name] = round(z_score, 2)

    if current_status == ServiceStatus.CRITICAL:
        service.consecutive_failures += 1
    else:
        service.consecutive_failures = 0

    if current_status == ServiceStatus.HEALTHY:
        service.consecutive_unhealthy = 0
        service.healthy_streak += 1
        service.last_healthy_at = time.time()
        service.guard_since = None
        if service.last_alerted_at is not None:
            logger.info("[ALERT] %s recovered", service.name)
        service.last_alerted_at = None
        service.anomaly_logged = False
    else:
        service.consecutive_unhealthy += 1
        service.healthy_streak = 0

    need = HEALER_RESTART_MIN_CONSECUTIVE

    if current_status == ServiceStatus.CRITICAL and service.consecutive_failures >= need:
        return True, f"CRITICAL: {service.consecutive_failures} consecutive failures", z_score

    if current_status == ServiceStatus.DEGRADED and service.consecutive_unhealthy >= need:
        return (
            True,
            f"DEGRADED: {service.consecutive_unhealthy} consecutive slow responses",
            z_score,
        )

    # A latency outlier alone is not enough: it must persist for `need` probes, otherwise a single slow
    # response while the host is busy restarts a perfectly good service.
    if (
        z_score > 3.0
        and current_status != ServiceStatus.HEALTHY
        and service.consecutive_unhealthy >= need
    ):
        return True, f"ANOMALY: Z-score={z_score:.1f} (threshold=3.0)", z_score

    return False, "nominal", z_score


# ------------------------------------
# HOST-LOAD GUARD
# ------------------------------------

@dataclass(frozen=True)
class HostLoad:
    """VM-wide load readings from /proc (None = could not be read)."""

    loadavg1: Optional[float] = None
    ncpu: int = 1
    cpu_pressure10: Optional[float] = None   # PSI /proc/pressure/cpu "some" avg10, percent of time stalled
    mem_available_mb: Optional[float] = None


@dataclass(frozen=True)
class GuardDecision:
    """Whether docker/http restarts should be held this cycle, and why."""

    hold: bool = False
    reason: str = ""


def read_host_load(proc_root: str = "/proc") -> HostLoad:
    """Read VM-wide load. /proc/loadavg, /proc/pressure/cpu and /proc/meminfo are not namespaced, so a container sees the
    whole VM. Anything unreadable stays None (the guard then ignores that signal)."""
    load1: Optional[float] = None
    pressure: Optional[float] = None
    mem_mb: Optional[float] = None
    try:
        with open(f"{proc_root}/loadavg", encoding="utf-8") as fh:
            load1 = float(fh.read().split()[0])
    except (OSError, ValueError, IndexError):
        pass
    try:
        with open(f"{proc_root}/pressure/cpu", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("some"):
                    m = re.search(r"avg10=([0-9.]+)", line)
                    if m:
                        pressure = float(m.group(1))
                    break
    except (OSError, ValueError):
        pass
    try:
        with open(f"{proc_root}/meminfo", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("MemAvailable:"):
                    mem_mb = int(line.split()[1]) / 1024.0
                    break
    except (OSError, ValueError, IndexError):
        pass
    return HostLoad(loadavg1=load1, ncpu=os.cpu_count() or 1, cpu_pressure10=pressure, mem_available_mb=mem_mb)


def evaluate_guard(
    services: list[ServiceConfig], load: HostLoad, now: Optional[float] = None
) -> GuardDecision:
    """Decide whether restarts are held this cycle. Pure function (inject `load`/`now` in tests)."""
    if not HEALER_LOAD_GUARD_ENABLED:
        return GuardDecision()
    now = time.time() if now is None else now
    reasons: list[str] = []

    if load.cpu_pressure10 is not None and load.cpu_pressure10 >= HEALER_LOAD_GUARD_CPU_PRESSURE:
        reasons.append(f"CPU pressure {load.cpu_pressure10:.0f}% >= {HEALER_LOAD_GUARD_CPU_PRESSURE:.0f}%")
    if load.loadavg1 is not None and load.ncpu > 0 and load.loadavg1 / load.ncpu >= HEALER_LOAD_GUARD_LOAD_PER_CPU:
        reasons.append(f"load {load.loadavg1:.1f} on {load.ncpu} CPUs")
    if (
        HEALER_LOAD_GUARD_MIN_MEM_MB > 0
        and load.mem_available_mb is not None
        and load.mem_available_mb < HEALER_LOAD_GUARD_MIN_MEM_MB
    ):
        reasons.append(f"only {load.mem_available_mb:.0f} MB memory available")

    # Systemic: several services that were healthy a moment ago are all unhealthy now. That points at the host, not at
    # any one service. Services that have been down for days (e.g. the stopped observability stack) were not recently
    # healthy and are not counted.
    if HEALER_LOAD_GUARD_SYSTEMIC_MIN >= 2:
        newly = [
            svc.name for svc in services
            if svc.last_status in (ServiceStatus.DEGRADED, ServiceStatus.CRITICAL)
            and svc.last_healthy_at is not None
            and (now - svc.last_healthy_at) <= HEALER_LOAD_GUARD_RECENT_HEALTHY_SECONDS
        ]
        if len(newly) >= HEALER_LOAD_GUARD_SYSTEMIC_MIN:
            reasons.append(f"{len(newly)} services went unhealthy at once ({', '.join(newly)})")

    return GuardDecision(hold=bool(reasons), reason="; ".join(reasons))


def _apply_guard(
    service: ServiceConfig, action: HealAction, guard: Optional[GuardDecision]
) -> HealAction:
    """Hold docker/http restarts while the host-load guard is active (alert-only actions are never held)."""
    if action not in (HealAction.DOCKER_RESTART, HealAction.HTTP_RESTART):
        return action
    if guard is not None and guard.hold:
        now = time.time()
        if service.guard_since is None:
            service.guard_since = now
            logger.warning(
                "[GUARD] %s restart HELD (up to %ds): %s", service.name, int(HEALER_LOAD_GUARD_MAX_HOLD_SECONDS), guard.reason
            )
        if now - service.guard_since < HEALER_LOAD_GUARD_MAX_HOLD_SECONDS:
            logger.debug("[GUARD] %s restart still held", service.name)
            return HealAction.NO_ACTION
        logger.warning(
            "[GUARD] %s held for %ds -- restarting anyway (guard max hold exceeded)",
            service.name, int(now - service.guard_since),
        )
        return action
    if service.guard_since is not None:
        logger.info("[GUARD] %s restart released after %ds", service.name, int(time.time() - service.guard_since))
        service.guard_since = None
    return action


# ------------------------------------
# PLAN PHASE
# ------------------------------------

def plan(
    service: ServiceConfig,
    _status: ServiceStatus,
    _reason: str,
    kb: KnowledgeBase,
    guard: Optional[GuardDecision] = None,
) -> HealAction:
    """Choose best heal action based on config and historical success rates."""
    if service.healing:
        logger.debug("[PLAN] %s -- a heal is already in flight, skipping", service.name)
        return HealAction.NO_ACTION

    # Exponential backoff — stop looping after repeated failed heals
    if service.backoff_until is not None and time.time() < service.backoff_until:
        remaining = int(service.backoff_until - time.time())
        logger.debug(
            "[PLAN] %s -- backoff active after %d failed heals (%ds remaining), skipping",
            service.name, service.consecutive_failed_heals, remaining,
        )
        return HealAction.NO_ACTION

    if service.last_healed and (time.time() - service.last_healed) < HEALER_COOLDOWN_SECONDS:
        logger.debug("[PLAN] %s -- cooldown active, skipping heal", service.name)
        return HealAction.NO_ACTION

    if not service.critical:
        now = time.time()
        if service.last_alerted_at is not None and (now - service.last_alerted_at) < HEALER_ALERT_REPEAT_SECONDS:
            logger.debug("[PLAN] %s -- already alerted %ds ago, skipping", service.name, int(now - service.last_alerted_at))
            return HealAction.NO_ACTION
        service.last_alerted_at = now
        return HealAction.ALERT_ONLY

    action = HealAction.ALERT_ONLY
    if service.restart_url:
        soft_rate = kb.success_rate(HealAction.HTTP_RESTART)
        if soft_rate >= 0.5 or not kb.action_success_rates[HealAction.HTTP_RESTART]:
            action = HealAction.HTTP_RESTART
    if action == HealAction.ALERT_ONLY and service.compose_name:
        action = HealAction.DOCKER_RESTART

    return _apply_guard(service, action, guard)


# ------------------------------------
# EXECUTE PHASE
# ------------------------------------

async def execute(
    service: ServiceConfig,
    action: HealAction,
    reason: str,
    kb: KnowledgeBase,
) -> HealEvent:
    """Apply the healing action and record the outcome."""
    started_at = time.time()
    success = False
    ts = datetime.now(tz=timezone.utc).isoformat()

    logger.warning(
        "[EXECUTE] Healing %s via %s -- %s", service.name, action.value, reason
    )

    if action == HealAction.HTTP_RESTART and service.restart_url:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(service.restart_url)
            success = resp.status_code < 400
        except Exception as exc:
            logger.error("[EXECUTE] HTTP restart failed: %s", exc)

    elif action == HealAction.DOCKER_RESTART and service.compose_name is not None:
        container_id: str = service.compose_name
        if not _DOCKER_AVAILABLE or docker_sdk is None:
            logger.error("[EXECUTE] docker SDK not available")
        else:
            try:
                def _do_restart() -> None:
                    """Synchronous docker restart -- run in thread."""
                    client = docker_sdk.DockerClient.from_env()
                    client.containers.get(container_id).restart()

                await asyncio.to_thread(_do_restart)
                success = True
                logger.info(
                    "[EXECUTE] Docker restart sent to %s", container_id
                )
            except Exception as exc:
                logger.error(
                    "[EXECUTE] Docker restart failed for %s: %s", container_id, exc
                )

    elif action == HealAction.ALERT_ONLY:
        success = True
        logger.warning("[ALERT] %s degraded -- %s", service.name, reason)

    elif action == HealAction.NO_ACTION:
        success = True

    mttr: Optional[float] = None
    if success and action not in (HealAction.NO_ACTION, HealAction.ALERT_ONLY):
        # A restarted service needs time to boot (hypercode-core ~90-230 s on this host): judging it after one
        # 5 s probe recorded EVERY restart as failed. Poll until it is HEALTHY or its grace period runs out.
        deadline = time.monotonic() + service.startup_grace_seconds
        recovered = False
        while True:
            await asyncio.sleep(HEALER_VERIFY_POLL_SECONDS)
            post_status, _ = await monitor(service)
            if post_status == ServiceStatus.HEALTHY:
                recovered = True
                break
            if time.monotonic() >= deadline:
                break
        if recovered:
            mttr = round(time.time() - started_at, 1)
            logger.info("[EXECUTE] %s recovered in %ss", service.name, mttr)
        else:
            success = False
            logger.warning(
                "[EXECUTE] %s still unhealthy after heal (waited %ss)",
                service.name, int(service.startup_grace_seconds),
            )

    service.total_heals += 1
    service.last_healed = time.time()

    # Track consecutive failed heals and apply exponential backoff
    if action not in (HealAction.NO_ACTION, HealAction.ALERT_ONLY):
        if success:
            if service.consecutive_failed_heals > 0:
                logger.info(
                    "[EXECUTE] %s recovered — resetting backoff (was %d failed heals)",
                    service.name, service.consecutive_failed_heals,
                )
            service.consecutive_failed_heals = 0
            service.backoff_until = None
        else:
            service.consecutive_failed_heals += 1
            if service.consecutive_failed_heals >= HEALER_MAX_RESTART_ATTEMPTS:
                backoff = min(
                    HEALER_BACKOFF_BASE_SECONDS * (2 ** (service.consecutive_failed_heals - HEALER_MAX_RESTART_ATTEMPTS)),
                    HEALER_MAX_BACKOFF_SECONDS,
                )
                service.backoff_until = time.time() + backoff
                logger.warning(
                    "[EXECUTE] %s — %d consecutive failed heals (max=%d). "
                    "Backing off for %ds (until %s).",
                    service.name,
                    service.consecutive_failed_heals,
                    HEALER_MAX_RESTART_ATTEMPTS,
                    backoff,
                    datetime.fromtimestamp(service.backoff_until, tz=timezone.utc).strftime("%H:%M:%S UTC"),
                )

    event = HealEvent(
        timestamp=ts,
        service=service.name,
        status_before=service.last_status,
        action_taken=action,
        success=success,
        reason=reason,
        mttr_seconds=mttr,
    )
    kb.record_heal(event)

    # Phase 10E: mirror MAPE-K heals into core's event stream, authed as US
    if action != HealAction.NO_ACTION:
        try:
            from core_events import publish_core_event
            await publish_core_event(
                "completed" if success else "failed",
                f"mapek-{service.name}",
                {"service": service.name, "action": action.value,
                 "reason": reason, "mttr_seconds": mttr},
            )
        except Exception as exc:
            logger.warning("Core event mirror failed (non-fatal): %s", exc)

    return event


# ------------------------------------
# HEAL SCHEDULING + BACKOFF RESET
# ------------------------------------

_background_heals: set[asyncio.Task[None]] = set()


def maybe_reset_backoff(service: ServiceConfig) -> bool:
    """Clear failed-heal state once a service has been HEALTHY long enough. Returns True if it reset."""
    if (
        service.healthy_streak >= HEALER_RESET_AFTER_HEALTHY
        and not service.healing
        and (service.consecutive_failed_heals > 0 or service.backoff_until is not None)
    ):
        logger.info(
            "[MAPE-K] %s healthy for %d probes -- resetting backoff (was %d failed heals)",
            service.name, service.healthy_streak, service.consecutive_failed_heals,
        )
        service.consecutive_failed_heals = 0
        service.backoff_until = None
        return True
    return False


async def _run_heal(
    service: ServiceConfig, action: HealAction, reason: str, kb: KnowledgeBase
) -> None:
    """Run one heal (incl. its post-restart verification) off the main loop; always clear `healing`."""
    try:
        await execute(service, action, reason, kb)
    except Exception as exc:
        logger.error("[MAPE-K] Heal of %s failed unexpectedly: %s", service.name, exc)
    finally:
        service.healing = False


def schedule_heal(
    service: ServiceConfig, action: HealAction, reason: str, kb: KnowledgeBase
) -> asyncio.Task[None]:
    """Start a heal in the background so verifying a slow-booting service never blocks monitoring of the rest."""
    service.healing = True
    task = asyncio.create_task(_run_heal(service, action, reason, kb))
    _background_heals.add(task)
    task.add_done_callback(_background_heals.discard)
    return task


# ------------------------------------
# MAPE-K MAIN LOOP
# ------------------------------------

async def _cycle_one(
    service: ServiceConfig,
    kb: KnowledgeBase,
    guard: GuardDecision,
    sem: asyncio.Semaphore,
) -> None:
    """One service's Monitor -> Analyze -> Plan -> (schedule) Execute step.

    Runs concurrently with the other services' steps, so a slow or hung probe delays only its own service. Everything after the
    probe is synchronous (no awaits), so the shared state it touches is never interleaved with another service's step.
    """
    try:
        async with sem:
            status, response_ms = await monitor(service)
        is_anomaly, reason, z_score = analyze(service, status, response_ms, kb)
        service.last_status = status
        maybe_reset_backoff(service)

        if is_anomaly:
            # WARNING once per episode (it stays an anomaly every 10 s until the service is healthy again)
            log = logger.debug if service.anomaly_logged else logger.warning
            service.anomaly_logged = True
            log(
                "[ANALYZE] %s anomaly detected! status=%s z=%.1f -- %s",
                service.name, status.value, z_score, reason,
            )
            action = plan(service, status, reason, kb, guard)
            if action != HealAction.NO_ACTION:
                schedule_heal(service, action, reason, kb)

    except Exception as exc:
        logger.error("[MAPE-K] Error processing %s: %s", service.name, exc)


async def mape_k_loop(
    services: list[ServiceConfig],
    kb: KnowledgeBase,
    interval_seconds: int = 10,
) -> None:
    """Core MAPE-K loop -- runs forever, monitors and heals all services (probed concurrently each cycle)."""
    logger.info("MAPE-K Engine ONLINE -- HyperCode self-healing active")
    guard_active = False

    while True:
        cycle_start = time.time()

        guard = evaluate_guard(services, read_host_load())
        if guard.hold != guard_active:
            if guard.hold:
                logger.warning("[GUARD] host-load guard ACTIVE -- docker/http restarts are held: %s", guard.reason)
            else:
                logger.info("[GUARD] host-load guard cleared -- restarts allowed again")
            guard_active = guard.hold

        sem = asyncio.Semaphore(max(1, HEALER_PROBE_CONCURRENCY))
        await asyncio.gather(*(_cycle_one(service, kb, guard, sem) for service in services))

        cycle_time = time.time() - cycle_start
        await asyncio.sleep(max(0.0, interval_seconds - cycle_time))


# ------------------------------------
# DEFAULT SERVICE REGISTRY
# ------------------------------------
# Internal Docker hostnames only -- NOT localhost.

DEFAULT_SERVICES: list[ServiceConfig] = [
    ServiceConfig(
        "HyperCode Backend", 8000,
        "http://hypercode-core:8000/health", "hypercode-core",
        probe_timeout=10.0, startup_grace_seconds=240.0),  # cold start is ~90-230 s (import time)
    ServiceConfig(
        "Healer Agent", 8008,
        "http://healer-agent:8008/health", "healer-agent", critical=False),
    # Alert-only: a docker restart of the dashboard under host load left it with a missing rootfs on 2026-10-12
    # (exec failed, probe unhealthy for ~19 h). Latency on the dashboard is not worth a restart; a human decides.
    ServiceConfig(
        "Mission Control", 3000,
        "http://hypercode-dashboard:3000/health", "hypercode-dashboard",
        critical=False, probe_timeout=10.0, startup_grace_seconds=90.0),
    ServiceConfig(
        "Ollama LLM", 11434,
        "http://hypercode-ollama:11434/api/tags", "hypercode-ollama",
        startup_grace_seconds=60.0),
    ServiceConfig(
        "Prometheus", 9090,
        "http://prometheus:9090/-/healthy", "prometheus", critical=False),
    ServiceConfig(
        "Grafana", 3000,
        "http://grafana:3000/api/health", "grafana", critical=False),
    ServiceConfig(
        "HyperHealth API", 8090,
        "http://hyperhealth-api:8090/health", "hyperhealth-api", critical=False),
]
