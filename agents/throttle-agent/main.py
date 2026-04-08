"""throttle-agent FastAPI service with advanced resource management."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from collections import deque
from datetime import datetime
from typing import Any

import httpx
from docker.errors import DockerException, NotFound
from fastapi import FastAPI, Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from pydantic import BaseModel

import docker


# Enhanced JSON logging
class JSONFormatter(logging.Formatter):
    """Format logs as JSON for better Loki integration."""

    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "component": record.name,
            "message": record.getMessage(),
        }
        # Add extra fields if present
        if hasattr(record, "action"):
            log_data["action"] = record.action
        if hasattr(record, "tier"):
            log_data["tier"] = record.tier
        if hasattr(record, "container"):
            log_data["container"] = record.container
        if hasattr(record, "ram_pct"):
            log_data["ram_pct"] = record.ram_pct
        if hasattr(record, "reason"):
            log_data["reason"] = record.reason
        if hasattr(record, "healer_ok"):
            log_data["healer_ok"] = record.healer_ok
        if hasattr(record, "duration_seconds"):
            log_data["duration_seconds"] = record.duration_seconds
        if hasattr(record, "error"):
            log_data["error"] = record.error
        return json.dumps(log_data)


logger = logging.getLogger("throttle-agent")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
logger.propagate = False

PROM_REGISTRY = CollectorRegistry()

# Core metrics
THROTTLE_ACTIONS_TOTAL = Counter(
    "throttle_actions_total",
    "Throttle actions executed",
    ["tier", "action", "container"],
    registry=PROM_REGISTRY,
)
DOCKER_UP = Gauge(
    "throttle_docker_up",
    "Whether docker daemon is reachable from throttle-agent (1/0)",
    registry=PROM_REGISTRY,
)
SYSTEM_RAM_USAGE_PCT = Gauge(
    "throttle_system_ram_usage_pct",
    "Estimated total RAM usage percentage (containers sum / docker mem total)",
    registry=PROM_REGISTRY,
)

TIER_PAUSED = Gauge(
    "throttle_tier_paused",
    "Whether a tier is currently paused by Throttle (1/0)",
    ["tier"],
    registry=PROM_REGISTRY,
)
CONTAINER_PAUSED_BY_THROTTLE = Gauge(
    "throttle_container_paused_by_throttle",
    "Whether a container is marked as paused by Throttle (1/0)",
    ["container_name"],
    registry=PROM_REGISTRY,
)
HEALER_CIRCUIT_OPEN = Gauge(
    "throttle_healer_circuit_open",
    "Whether Healer circuit breaker is open for a service (1/0)",
    ["service_name"],
    registry=PROM_REGISTRY,
)
RAM_THRESHOLD_PCT = Gauge(
    "throttle_ram_threshold_pct",
    "Current configured RAM thresholds used by Throttle",
    ["level"],
    registry=PROM_REGISTRY,
)

CONTAINER_STATE = Gauge(
    "throttle_container_state",
    "Container state as a gauge (labels include state)",
    ["name", "state"],
    registry=PROM_REGISTRY,
)
CONTAINER_RAM_BYTES = Gauge(
    "throttle_container_ram_bytes",
    "Container memory usage in bytes",
    ["name"],
    registry=PROM_REGISTRY,
)

# Enhanced metrics for better observability
THROTTLE_DECISION_REASONS = Counter(
    "throttle_decision_reasons",
    "Reasons for throttle decisions",
    ["reason", "tier"],
    registry=PROM_REGISTRY,
)
THROTTLE_PAUSE_DURATION_SECONDS = Histogram(
    "throttle_pause_duration_seconds",
    "How long containers stay paused",
    buckets=[60, 300, 900, 1800, 3600, 7200],
    registry=PROM_REGISTRY,
)
CONTAINER_CPU_PERCENT = Gauge(
    "throttle_container_cpu_percent",
    "Container CPU usage percentage",
    ["name"],
    registry=PROM_REGISTRY,
)
CONTAINER_NETWORK_RX_BYTES = Gauge(
    "throttle_container_network_rx_bytes",
    "Network bytes received",
    ["name"],
    registry=PROM_REGISTRY,
)
CONTAINER_NETWORK_TX_BYTES = Gauge(
    "throttle_container_network_tx_bytes",
    "Network bytes transmitted",
    ["name"],
    registry=PROM_REGISTRY,
)
HEALTH_CHECK_DURATION_SECONDS = Histogram(
    "throttle_health_check_duration_seconds",
    "Duration of health checks",
    buckets=[0.1, 0.5, 1, 2, 5, 10],
    registry=PROM_REGISTRY,
)
DECISION_CALCULATION_DURATION_SECONDS = Histogram(
    "throttle_decision_calculation_duration_seconds",
    "Duration of decision calculations",
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 5],
    registry=PROM_REGISTRY,
)

# RAM history for predictions
ram_history: deque = deque(maxlen=30)  # Keep last 30 measurements

DEFAULT_TIERS: dict[int, list[str]] = {
    1: ["postgres", "redis", "hypercode-core", "hypercode-ollama"],
    2: ["crew-orchestrator", "hypercode-dashboard"],
    3: ["celery-worker"],
    4: ["test-agent"],
    5: ["prometheus", "tempo", "loki", "grafana"],
    6: ["minio", "cadvisor", "node-exporter", "security-scanner"],
}

ALL_CONTAINERS: list[str] = sorted({c for tier in DEFAULT_TIERS.values() for c in tier})


class TierContainerStatus(BaseModel):
    name: str
    status: str | None = None
    health: str | None = None
    ram_bytes: int | None = None
    error: str | None = None


class TierStatus(BaseModel):
    tier: int
    containers: list[TierContainerStatus]
    running: int
    healthy: int


def _docker_client() -> docker.DockerClient:
    return docker.from_env()


def _container_health(container: Any) -> str | None:
    state = container.attrs.get("State", {})
    health = state.get("Health")
    if isinstance(health, dict):
        status = health.get("Status")
        if isinstance(status, str):
            return status
    return None


def _container_state(container: Any) -> str | None:
    state = container.attrs.get("State", {})
    status = state.get("Status")
    if isinstance(status, str):
        return status
    return None


def _container_ram_bytes(container: Any) -> int | None:
    try:
        stats = container.stats(stream=False)
        mem = stats.get("memory_stats", {})
        usage = mem.get("usage")
        if isinstance(usage, int):
            return usage
        return None
    except Exception:
        return None


def _docker_mem_total_bytes(client: docker.DockerClient) -> int | None:
    try:
        info = client.api.info()
        mem_total = info.get("MemTotal")
        if isinstance(mem_total, int) and mem_total > 0:
            return mem_total
        return None
    except Exception:
        return None


def _estimate_system_ram_pct(
    client: docker.DockerClient, tiers: dict[int, list[str]]
) -> float | None:
    mem_total = _docker_mem_total_bytes(client)
    if not mem_total:
        return None
    usage_sum = 0
    for _, names in tiers.items():
        for name in names:
            try:
                container = client.containers.get(name)
                ram = _container_ram_bytes(container)
                if isinstance(ram, int):
                    usage_sum += ram
            except Exception:
                continue
    return round((usage_sum / mem_total) * 100, 2)


def _reset_container_state_gauges(name: str) -> None:
    for state in (
        "created",
        "running",
        "paused",
        "restarting",
        "removing",
        "exited",
        "dead",
        "unknown",
    ):
        try:
            CONTAINER_STATE.labels(name=name, state=state).set(0)
        except Exception:
            continue


def _record_container_metrics(status: TierContainerStatus) -> None:
    _reset_container_state_gauges(status.name)
    state = status.status or "unknown"
    CONTAINER_STATE.labels(name=status.name, state=state).set(1)
    if isinstance(status.ram_bytes, int):
        CONTAINER_RAM_BYTES.labels(name=status.name).set(status.ram_bytes)


def _get_tier_status(
    client: docker.DockerClient, tier: int, names: list[str]
) -> TierStatus:
    containers: list[TierContainerStatus] = []
    running = 0
    healthy = 0

    for name in names:
        try:
            container = client.containers.get(name)
            container.reload()
            _record_container_advanced_stats(name, container)
            status = _container_state(container)
            health = _container_health(container)
            ram = _container_ram_bytes(container)
            if status == "running":
                running += 1
            if health == "healthy":
                healthy += 1
            containers.append(
                TierContainerStatus(
                    name=name, status=status, health=health, ram_bytes=ram
                )
            )
        except NotFound:
            containers.append(TierContainerStatus(name=name, error="not_found"))
        except DockerException as e:
            containers.append(TierContainerStatus(name=name, error=str(e)))
        except Exception as e:
            containers.append(TierContainerStatus(name=name, error=str(e)))

    for c in containers:
        _record_container_metrics(c)

    return TierStatus(
        tier=tier, containers=containers, running=running, healthy=healthy
    )


def _get_tiers() -> dict[int, list[str]]:
    return DEFAULT_TIERS


def _parse_threshold(name: str, default: float) -> float:
    raw = os.getenv(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


HEALER_URL = (
    os.getenv("HEALER_URL", "http://healer-agent:8008").strip()
    or "http://healer-agent:8008"
)

MEMSTREAM_URL = os.getenv("MEMSTREAM_URL", "http://127.0.0.1:8010").strip() or "http://127.0.0.1:8010"
MEMSTREAM_TOKEN = os.getenv("MEMSTREAM_HEALTH_TOKEN", "").strip()

AUTO_THROTTLE_ENABLED = os.getenv("AUTO_THROTTLE_ENABLED", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

THROTTLE_PAUSE_TIER6_AT = _parse_threshold("THROTTLE_PAUSE_TIER6_AT", 80.0)
THROTTLE_PAUSE_TIER5_AT = _parse_threshold("THROTTLE_PAUSE_TIER5_AT", 90.0)
THROTTLE_PAUSE_TIER4_AT = _parse_threshold("THROTTLE_PAUSE_TIER4_AT", 95.0)
THROTTLE_RESUME_BELOW = _parse_threshold("THROTTLE_RESUME_BELOW", 75.0)
THROTTLE_RESUME_HOLD_MINUTES = int(
    _parse_threshold("THROTTLE_RESUME_HOLD_MINUTES", 5.0)
)
THROTTLE_PAUSE_TTL_SECONDS = int(_parse_threshold("THROTTLE_PAUSE_TTL_SECONDS", 900.0))
THROTTLE_KEEP_OBSERVABILITY = os.getenv(
    "THROTTLE_KEEP_OBSERVABILITY", "true"
).strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
POLL_INTERVAL_SECONDS = int(_parse_threshold("POLL_INTERVAL_SECONDS", 30.0))


async def poll_memstream_and_throttle() -> None:
    pressure_to_delay = {"🟢 LOW": 0, "🟡 MEDIUM": 200, "🔴 HIGH": 500}
    while True:
        try:
            r = httpx.get(
                f"{MEMSTREAM_URL}/health/memstream",
                headers={"Authorization": f"Bearer {MEMSTREAM_TOKEN}"},
                timeout=2.0,
            )
            pressure = "🟢 LOW"
            if r.status_code == 200:
                pressure = (r.json() or {}).get("pressure", "🟢 LOW")
            else:
                print(f"[Throttle] Health poll failed: {r.status_code}")
            delay = pressure_to_delay.get(pressure, 0)
            last_status: int | None = None
            for attempt in range(2):
                resp = httpx.post(
                    f"{MEMSTREAM_URL}/throttle",
                    json={"delay_ms": delay},
                    headers={"Authorization": f"Bearer {MEMSTREAM_TOKEN}"},
                    timeout=2.0,
                )
                last_status = resp.status_code
                if resp.status_code == 200:
                    break
                if attempt == 0 and resp.status_code in {408, 429, 500, 502, 503, 504}:
                    await asyncio.sleep(0.5)
                    continue
                break
            if last_status != 200:
                print(f"[Throttle] Throttle failed: {last_status}")
            print(f"[Throttle] {pressure} → delay {delay}ms")
        except Exception as e:
            print(f"[Throttle] MemStream unreachable: {e}")
        await asyncio.sleep(10)


def _parse_int_set(raw: str) -> set[int]:
    out: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.add(int(part))
        except ValueError:
            continue
    return out


def _parse_str_set(raw: str) -> set[str]:
    return {p.strip() for p in raw.split(",") if p.strip()}


THROTTLE_PROTECT_TIERS = _parse_int_set(os.getenv("THROTTLE_PROTECT_TIERS", "1,2,3"))
THROTTLE_PROTECT_CONTAINERS = _parse_str_set(
    os.getenv(
        "THROTTLE_PROTECT_CONTAINERS",
        "throttle-agent,healer-agent,hypercode-core,postgres,redis",
    )
)
THROTTLE_ACTIVE_CONTAINER = os.getenv("THROTTLE_ACTIVE_CONTAINER", "").strip()
if THROTTLE_ACTIVE_CONTAINER:
    THROTTLE_PROTECT_CONTAINERS.add(THROTTLE_ACTIVE_CONTAINER)

import threading as _threading

app = FastAPI(title="Throttle Agent")

_throttle_lock = _threading.Lock()
_started_at: float = time.time()
_last_poll_ts: float = 0.0
_last_ram_pct: float | None = None
_autopilot_below_since: float | None = None
_autopilot_paused_tiers: set[int] = set()
_last_healer_state_poll_ts: float = 0.0
_last_paused_by_throttle: set[str] = set()
_last_open_circuits: set[str] = set()
_paused_since: dict[str, float] = {}


def _fetch_healer_paused_by_throttle() -> set[str]:
    try:
        r = httpx.get(f"{HEALER_URL}/throttle/state", timeout=2.0)
        if r.status_code != 200:
            return set()
        data = r.json()
        containers = data.get("containers", [])
        if not isinstance(containers, list):
            return set()
        return {c for c in containers if isinstance(c, str) and c}
    except Exception:
        return set()


def _fetch_healer_open_circuits() -> set[str]:
    try:
        r = httpx.get(f"{HEALER_URL}/circuit-breaker/status", timeout=2.0)
        if r.status_code != 200:
            return set()
        data = r.json()
        open_circuits = data.get("open_circuits", [])
        if not isinstance(open_circuits, list):
            return set()
        return {c for c in open_circuits if isinstance(c, str) and c}
    except Exception:
        return set()


def _update_grafana_metrics() -> None:
    global _last_healer_state_poll_ts, _last_paused_by_throttle, _last_open_circuits

    RAM_THRESHOLD_PCT.labels(level="pause_tier6_at").set(THROTTLE_PAUSE_TIER6_AT)
    RAM_THRESHOLD_PCT.labels(level="pause_tier5_at").set(THROTTLE_PAUSE_TIER5_AT)
    RAM_THRESHOLD_PCT.labels(level="pause_tier4_at").set(THROTTLE_PAUSE_TIER4_AT)
    RAM_THRESHOLD_PCT.labels(level="resume_below").set(THROTTLE_RESUME_BELOW)

    now = time.time()
    if now - _last_healer_state_poll_ts >= 10:
        _last_healer_state_poll_ts = now
        _last_paused_by_throttle = _fetch_healer_paused_by_throttle()
        _last_open_circuits = _fetch_healer_open_circuits()

    paused = _last_paused_by_throttle
    for c in ALL_CONTAINERS:
        CONTAINER_PAUSED_BY_THROTTLE.labels(container_name=c).set(
            1 if c in paused else 0
        )

    for tier, containers in _get_tiers().items():
        tier_paused = any(c in paused for c in containers)
        TIER_PAUSED.labels(tier=str(tier)).set(1 if tier_paused else 0)

    open_circuits = _last_open_circuits
    for c in ALL_CONTAINERS:
        HEALER_CIRCUIT_OPEN.labels(service_name=c).set(1 if c in open_circuits else 0)


def _notify_healer_state(containers: list[str], paused: bool) -> None:
    if not containers:
        return
    payload = {
        "containers": containers,
        "paused": paused,
        "ttl_seconds": THROTTLE_PAUSE_TTL_SECONDS,
        "reason": "throttle_agent",
    }
    try:
        resp = httpx.post(f"{HEALER_URL}/throttle/state", json=payload, timeout=2.0)
        resp.raise_for_status()
    except Exception as e:
        logger.warning("Healer notification failed, will retry next cycle", extra={"error": str(e)})


def _healer_allows_resume(container: str) -> bool:
    try:
        r = httpx.get(f"{HEALER_URL}/circuit-breaker/{container}", timeout=2.0)
        if r.status_code != 200:
            return True
        data = r.json()
        return data.get("state") != "open"
    except Exception:
        return True


def _tier_container_names(tier: int) -> list[str]:
    tiers = _get_tiers()
    return list(tiers.get(tier, []))


def _predict_ram_usage(minutes_ahead: int) -> float | None:
    """Predict RAM usage N minutes ahead using linear trend."""
    if len(ram_history) < 3:
        return None

    try:
        recent_values = list(ram_history)[-5:]
        if len(recent_values) < 2:
            return None

        # Simple linear regression
        n = len(recent_values)
        x_values = list(range(n))
        x_mean = sum(x_values) / n
        y_mean = sum(recent_values) / n

        numerator = sum(
            (x_values[i] - x_mean) * (recent_values[i] - y_mean) for i in range(n)
        )
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return recent_values[-1]

        slope = numerator / denominator
        steps_ahead = max(
            int(round((minutes_ahead * 60) / max(POLL_INTERVAL_SECONDS, 1))), 1
        )
        predicted = recent_values[-1] + (slope * steps_ahead)
        return round(max(0, predicted), 2)  # Clamp to >= 0
    except Exception:
        return None


def _record_container_advanced_stats(container_name: str, container: Any) -> None:
    """Record advanced container statistics (CPU, network)."""
    try:
        stats = container.stats(stream=False)

        # Calculate CPU percentage
        cpu_stats = stats.get("cpu_stats", {})
        prev_cpu_stats = stats.get("precpu_stats", {})

        cpu_delta = cpu_stats.get("cpu_usage", {}).get(
            "total_usage", 0
        ) - prev_cpu_stats.get("cpu_usage", {}).get("total_usage", 0)
        system_delta = cpu_stats.get("system_cpu_usage", 0) - prev_cpu_stats.get(
            "system_cpu_usage", 0
        )
        cpu_count = cpu_stats.get("online_cpus", 1) or len(cpu_stats.get("cpus", [0]))

        if system_delta > 0:
            cpu_percent = (cpu_delta / system_delta) * 100.0 * cpu_count
            CONTAINER_CPU_PERCENT.labels(name=container_name).set(round(cpu_percent, 2))

        # Record network stats
        networks = stats.get("networks", {})
        rx_bytes = sum(net.get("rx_bytes", 0) for net in networks.values())
        tx_bytes = sum(net.get("tx_bytes", 0) for net in networks.values())

        CONTAINER_NETWORK_RX_BYTES.labels(name=container_name).set(rx_bytes)
        CONTAINER_NETWORK_TX_BYTES.labels(name=container_name).set(tx_bytes)
    except Exception:
        pass  # Silently skip if stats unavailable


def _pause_tier_sync(client: docker.DockerClient, tier: int) -> dict[str, Any]:
    changed: list[str] = []
    failed: dict[str, str] = {}
    targets = _tier_container_names(tier)

    for name in targets:
        if name in THROTTLE_PROTECT_CONTAINERS:
            logger.info(
                "Skipping pause of protected container",
                extra={
                    "action": "pause_skip_protected",
                    "tier": tier,
                    "container": name,
                },
            )
            continue
        try:
            container = client.containers.get(name)
            container.pause()
            THROTTLE_ACTIONS_TOTAL.labels(
                tier=str(tier), action="pause", container=name
            ).inc()
            changed.append(name)
            _paused_since[name] = time.time()
            logger.info(
                "Paused container",
                extra={"action": "pause", "tier": tier, "container": name},
            )
        except Exception as e:
            failed[name] = str(e)
            logger.error(
                "Failed to pause container",
                extra={
                    "action": "pause_error",
                    "tier": tier,
                    "container": name,
                    "error": str(e),
                },
            )

    if changed:
        _notify_healer_state(changed, paused=True)

    return {"tier": tier, "action": "pause", "changed": changed, "failed": failed}


def _resume_tier_sync(client: docker.DockerClient, tier: int) -> dict[str, Any]:
    changed: list[str] = []
    failed: dict[str, str] = {}
    skipped: list[str] = []
    targets = _tier_container_names(tier)
    for name in targets:
        if name in THROTTLE_PROTECT_CONTAINERS:
            continue
        if not _healer_allows_resume(name):
            skipped.append(name)
            continue
        try:
            container = client.containers.get(name)
            container.unpause()
            THROTTLE_ACTIONS_TOTAL.labels(
                tier=str(tier), action="resume", container=name
            ).inc()
            changed.append(name)
            paused_at = _paused_since.pop(name, None)
            if paused_at is not None:
                THROTTLE_PAUSE_DURATION_SECONDS.observe(
                    max(time.time() - paused_at, 0.0)
                )
        except Exception as e:
            failed[name] = str(e)
    if changed:
        _notify_healer_state(changed, paused=False)
    return {
        "tier": tier,
        "action": "resume",
        "changed": changed,
        "skipped": skipped,
        "failed": failed,
    }


def _autopilot_cycle_sync() -> None:
    global _autopilot_below_since, _autopilot_paused_tiers, _last_poll_ts, _last_ram_pct

    tiers_cfg = _get_tiers()
    client = _docker_client()
    client.ping()
    DOCKER_UP.set(1)

    current_ram = _estimate_system_ram_pct(client, tiers_cfg)
    now = time.time()

    with _throttle_lock:
        _last_poll_ts = now
        _last_ram_pct = current_ram

    if current_ram is not None:
        SYSTEM_RAM_USAGE_PCT.set(current_ram)
        ram_history.append(current_ram)

    _update_grafana_metrics()

    ram_pct = current_ram
    if ram_pct is None:
        return

    desired_pause: list[int] = []
    if ram_pct >= THROTTLE_PAUSE_TIER4_AT:
        desired_pause = [6, 5, 4]
    elif ram_pct >= THROTTLE_PAUSE_TIER5_AT:
        desired_pause = [6, 5]
    elif ram_pct >= THROTTLE_PAUSE_TIER6_AT:
        desired_pause = [6]

    if THROTTLE_KEEP_OBSERVABILITY and ram_pct < THROTTLE_PAUSE_TIER5_AT:
        desired_pause = [t for t in desired_pause if t != 5]

    with _throttle_lock:
        for tier in desired_pause:
            if tier in THROTTLE_PROTECT_TIERS:
                continue
            if tier in _autopilot_paused_tiers:
                continue
            _pause_tier_sync(client, tier)
            _autopilot_paused_tiers.add(tier)

        if ram_pct < THROTTLE_RESUME_BELOW:
            if _autopilot_below_since is None:
                _autopilot_below_since = time.time()
        else:
            _autopilot_below_since = None

        if _autopilot_paused_tiers and _autopilot_below_since is not None:
            hold_seconds = max(THROTTLE_RESUME_HOLD_MINUTES, 1) * 60
            if time.time() - _autopilot_below_since >= hold_seconds:
                for tier in [4, 5, 6]:
                    if tier in _autopilot_paused_tiers:
                        _resume_tier_sync(client, tier)
                        _autopilot_paused_tiers.remove(tier)
                if not _autopilot_paused_tiers:
                    _autopilot_below_since = None


@app.on_event("startup")
async def startup() -> None:
    if AUTO_THROTTLE_ENABLED:
        logger.info("AUTO_THROTTLE_ENABLED is true")
        asyncio.create_task(_autopilot_loop())
    else:
        logger.info("AUTO_THROTTLE_ENABLED is false")
    asyncio.create_task(poll_memstream_and_throttle())


async def _autopilot_loop() -> None:
    while True:
        try:
            await asyncio.to_thread(_autopilot_cycle_sync)
        except Exception as e:
            logger.error(f"Autopilot error: {e}", extra={"action": "autopilot_error"})
        await asyncio.sleep(max(POLL_INTERVAL_SECONDS, 5))


@app.get("/health")
def health() -> dict[str, Any]:
    import time as time_module

    start = time_module.time()

    healer_ok: bool | None = None
    try:
        r = httpx.get(f"{HEALER_URL}/health", timeout=2.0)
        healer_ok = r.status_code == 200
    except Exception:
        healer_ok = None
    try:
        _docker_client().ping()
        DOCKER_UP.set(1)
        duration = time_module.time() - start
        HEALTH_CHECK_DURATION_SECONDS.observe(duration)
        logger.info(
            "Health check passed",
            extra={
                "action": "health_check",
                "healer_ok": healer_ok,
                "duration_seconds": round(duration, 4),
            },
        )
        return {
            "status": "healthy",
            "agent": "throttle-agent",
            "docker": "ok",
            "healer_ok": healer_ok,
            "uptime_seconds": round(time_module.time() - _started_at, 3),
        }
    except Exception as e:
        DOCKER_UP.set(0)
        duration = time_module.time() - start
        HEALTH_CHECK_DURATION_SECONDS.observe(duration)
        logger.error(
            "Health check failed",
            extra={
                "action": "health_check_error",
                "healer_ok": healer_ok,
                "duration_seconds": round(duration, 4),
                "error": str(e),
            },
        )
        return {
            "status": "degraded",
            "agent": "throttle-agent",
            "docker": "error",
            "detail": str(e),
            "healer_ok": healer_ok,
        }


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(PROM_REGISTRY), media_type=CONTENT_TYPE_LATEST)


@app.get("/tiers")
def tiers() -> dict[str, Any]:
    tiers_cfg = _get_tiers()
    try:
        client = _docker_client()
        client.ping()
        DOCKER_UP.set(1)
    except Exception as e:
        DOCKER_UP.set(0)
        return {"error": "docker_unreachable", "detail": str(e)}

    data: dict[int, TierStatus] = {}
    for tier, names in tiers_cfg.items():
        data[tier] = _get_tier_status(client, tier, names)
    _update_grafana_metrics()
    return {"tiers": {k: v.model_dump() for k, v in data.items()}}


@app.get("/decisions")
def decisions() -> dict[str, Any]:
    global _last_poll_ts, _last_ram_pct
    start = time.time()

    tiers_cfg = _get_tiers()
    try:
        client = _docker_client()
        client.ping()
        DOCKER_UP.set(1)
    except Exception as e:
        DOCKER_UP.set(0)
        logger.error(
            "Docker unreachable in decisions",
            extra={"action": "decisions_docker_unreachable", "error": str(e)},
        )
        return {"error": "docker_unreachable", "detail": str(e)}

    now = time.time()
    with _throttle_lock:
        needs_poll = now - _last_poll_ts > POLL_INTERVAL_SECONDS or _last_ram_pct is None
    if needs_poll:
        current_ram = _estimate_system_ram_pct(client, tiers_cfg)
        with _throttle_lock:
            _last_poll_ts = now
            _last_ram_pct = current_ram
        if current_ram is not None:
            SYSTEM_RAM_USAGE_PCT.set(current_ram)
            ram_history.append(current_ram)

    _update_grafana_metrics()

    with _throttle_lock:
        ram_pct = _last_ram_pct
    actions: list[str] = []
    reason = "unknown"

    if ram_pct is None:
        actions.append("UNKNOWN: cannot determine system RAM usage")
        reason = "unknown_ram"
    elif ram_pct >= THROTTLE_PAUSE_TIER4_AT:
        actions.append("EMERGENCY: pause tier 6, then tier 5, then tier 4")
        reason = "emergency_tier4"
        THROTTLE_DECISION_REASONS.labels(reason="emergency_tier4", tier="4").inc()
    elif ram_pct >= THROTTLE_PAUSE_TIER5_AT:
        actions.append("HIGH: pause tier 6, then tier 5")
        reason = "high_tier5"
        THROTTLE_DECISION_REASONS.labels(reason="high_tier5", tier="5").inc()
    elif ram_pct >= THROTTLE_PAUSE_TIER6_AT:
        actions.append("WARN: consider pausing tier 6")
        reason = "warn_tier6"
        THROTTLE_DECISION_REASONS.labels(reason="warn_tier6", tier="6").inc()
    else:
        actions.append("ALL GREEN")
        reason = "all_green"

    # Predict future RAM usage
    predicted_ram = _predict_ram_usage(5) if len(ram_history) >= 5 else None

    duration = time.time() - start
    DECISION_CALCULATION_DURATION_SECONDS.observe(duration)

    logger.info(
        "Decision calculated",
        extra={
            "action": "decision",
            "ram_pct": ram_pct,
            "reason": reason,
            "duration_seconds": round(duration, 4),
        },
    )

    return {
        "auto_throttle_enabled": AUTO_THROTTLE_ENABLED,
        "ram_pct": ram_pct,
        "predicted_ram_5min": predicted_ram,
        "thresholds": {
            "pause_tier6_at": THROTTLE_PAUSE_TIER6_AT,
            "pause_tier5_at": THROTTLE_PAUSE_TIER5_AT,
            "pause_tier4_at": THROTTLE_PAUSE_TIER4_AT,
            "resume_below": THROTTLE_RESUME_BELOW,
            "resume_hold_minutes": THROTTLE_RESUME_HOLD_MINUTES,
        },
        "protect": {
            "tiers": sorted(THROTTLE_PROTECT_TIERS),
            "containers": sorted(THROTTLE_PROTECT_CONTAINERS),
            "active_container": THROTTLE_ACTIVE_CONTAINER or None,
            "keep_observability": THROTTLE_KEEP_OBSERVABILITY,
        },
        "autopilot": {
            "paused_tiers": sorted(_autopilot_paused_tiers),
            "poll_interval_seconds": POLL_INTERVAL_SECONDS,
        },
        "healer_url": HEALER_URL,
        "actions": actions,
    }


@app.post("/throttle/{tier}")
def throttle_tier(tier: int, request: Request, action: str = "pause") -> dict[str, Any]:
    tiers_cfg = _get_tiers()
    if tier not in tiers_cfg:
        return {"error": "invalid_tier", "tier": tier}

    if action not in {"pause", "resume"}:
        return {"error": "invalid_action", "action": action}

    api_key = os.getenv("THROTTLE_API_KEY", "").strip()
    if api_key:
        provided = request.headers.get("x-api-key", "").strip()
        if not provided or provided != api_key:
            return {"error": "unauthorized"}

    try:
        client = _docker_client()
        client.ping()
        DOCKER_UP.set(1)
    except Exception as e:
        DOCKER_UP.set(0)
        return {"error": "docker_unreachable", "detail": str(e)}

    if action == "pause":
        return _pause_tier_sync(client, tier)
    return _resume_tier_sync(client, tier)
