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

import httpx

try:
    import docker as docker_sdk  # type: ignore[import]
    _DOCKER_AVAILABLE = True
except ImportError:
    docker_sdk = None  # type: ignore[assignment]
    _DOCKER_AVAILABLE = False

logger = logging.getLogger("mape_k")


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
    history: deque[tuple[float, ServiceStatus, float]] = field(
        default_factory=lambda: deque(maxlen=60)
    )
    last_status: ServiceStatus = ServiceStatus.UNKNOWN
    consecutive_failures: int = 0
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
        async with httpx.AsyncClient(timeout=5.0) as client:
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

    if current_status == ServiceStatus.CRITICAL and service.consecutive_failures >= 2:
        return True, f"CRITICAL: {service.consecutive_failures} consecutive failures", z_score

    if current_status == ServiceStatus.DEGRADED and service.consecutive_failures >= 3:
        return (
            True,
            f"DEGRADED: {service.consecutive_failures} consecutive slow responses",
            z_score,
        )

    if z_score > 3.0 and current_status != ServiceStatus.HEALTHY:
        return True, f"ANOMALY: Z-score={z_score:.1f} (threshold=3.0)", z_score

    return False, "nominal", z_score


# ------------------------------------
# PLAN PHASE
# ------------------------------------

def plan(
    service: ServiceConfig,
    _status: ServiceStatus,
    _reason: str,
    kb: KnowledgeBase,
) -> HealAction:
    """Choose best heal action based on config and historical success rates."""
    # Exponential backoff — stop looping after repeated failed heals
    if service.backoff_until is not None and time.time() < service.backoff_until:
        remaining = int(service.backoff_until - time.time())
        logger.info(
            "[PLAN] %s -- backoff active after %d failed heals (%ds remaining), skipping",
            service.name, service.consecutive_failed_heals, remaining,
        )
        return HealAction.NO_ACTION

    if service.last_healed and (time.time() - service.last_healed) < 60:
        logger.info("[PLAN] %s -- cooldown active, skipping heal", service.name)
        return HealAction.NO_ACTION

    if not service.critical:
        return HealAction.ALERT_ONLY

    if service.restart_url:
        soft_rate = kb.success_rate(HealAction.HTTP_RESTART)
        if soft_rate >= 0.5 or not kb.action_success_rates[HealAction.HTTP_RESTART]:
            return HealAction.HTTP_RESTART

    if service.compose_name:
        return HealAction.DOCKER_RESTART

    return HealAction.ALERT_ONLY


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
        await asyncio.sleep(5)
        post_status, _ = await monitor(service)
        if post_status == ServiceStatus.HEALTHY:
            mttr = round(time.time() - started_at, 1)
            logger.info("[EXECUTE] %s recovered in %ss", service.name, mttr)
        else:
            success = False
            logger.warning(
                "[EXECUTE] %s still unhealthy after heal", service.name
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
    return event


# ------------------------------------
# MAPE-K MAIN LOOP
# ------------------------------------

async def mape_k_loop(
    services: list[ServiceConfig],
    kb: KnowledgeBase,
    interval_seconds: int = 10,
) -> None:
    """Core MAPE-K loop -- runs forever, monitors and heals all services."""
    logger.info("MAPE-K Engine ONLINE -- HyperCode self-healing active")

    while True:
        cycle_start = time.time()

        for service in services:
            try:
                status, response_ms = await monitor(service)
                is_anomaly, reason, z_score = analyze(
                    service, status, response_ms, kb
                )
                service.last_status = status

                if is_anomaly:
                    logger.warning(
                        "[ANALYZE] %s anomaly detected! status=%s z=%.1f -- %s",
                        service.name, status.value, z_score, reason,
                    )
                    action = plan(service, status, reason, kb)
                    if action != HealAction.NO_ACTION:
                        _ = await execute(service, action, reason, kb)

            except Exception as exc:
                logger.error(
                    "[MAPE-K] Error processing %s: %s", service.name, exc
                )

        cycle_time = time.time() - cycle_start
        await asyncio.sleep(max(0.0, interval_seconds - cycle_time))


# ------------------------------------
# DEFAULT SERVICE REGISTRY
# ------------------------------------
# Internal Docker hostnames only -- NOT localhost.

DEFAULT_SERVICES: list[ServiceConfig] = [
    ServiceConfig(
        "HyperCode Backend", 8000,
        "http://hypercode-core:8000/health", "hypercode-core"),
    ServiceConfig(
        "Healer Agent", 8008,
        "http://healer-agent:8008/health", "healer-agent", critical=False),
    ServiceConfig(
        "Crew Orchestrator", 8080,
        "http://crew-orchestrator:8080/health", "crew-orchestrator"),
    ServiceConfig(
        "Super BROski Agent", 8015,
        "http://super-hyper-broski-agent:8015/health",
        "super-hyper-broski-agent"),
    # throttle-agent not deployed in current stack — removed from monitor list
    ServiceConfig(
        "Test Agent", 8080,
        "http://test-agent:8080/health", "test-agent"),
    ServiceConfig(
        "Tips Writer", 8009,
        "http://tips-tricks-writer:8009/health", "tips-tricks-writer"),
    ServiceConfig(
        "Mission Control", 3000,
        "http://hypercode-dashboard:3000/health", "hypercode-dashboard"),
    # mcp-gateway and mcp-rest-adapter not deployed in current stack — removed from monitor list
    ServiceConfig(
        "Ollama LLM", 11434,
        "http://hypercode-ollama:11434/api/tags", "hypercode-ollama"),
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
