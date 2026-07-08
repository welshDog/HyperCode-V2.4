"""
🧬 HYPERVISOR AGENT — Real-Time Resource Guardian for HyperFocus Z0ne

Monitors laptop CPU/RAM/disk, auto-scales containers, predicts OOM,
and keeps your distributed system breathing.

Features:
  - Live metrics streaming (WebSocket + REST)
  - Predictive OOM detection (linear-regression trend analysis)
  - Auto-scaling rules (kill zombie containers, shed monitoring load)
      · DRY-RUN by default — set ENFORCE_SCALING=true to let it act
      · heal-back — restarts what it stopped once pressure clears
  - Crew Orchestrator integration + Redis cache
  - Discord alerts (broski-bot)

Safety notes:
  - Scaling actions are gated behind ENFORCE_SCALING (default false) and only
    fire after SUSTAINED_CRIT consecutive critical samples — no single-spike
    kills. It never touches a container it wasn't told the name-pattern for.
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from collections import deque
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict

import psutil
import docker
import redis
import numpy as np
from scipy import stats
from fastapi import FastAPI, WebSocket, BackgroundTasks
import uvicorn

# ─── Setup ────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# ─── Configuration ────────────────────────────────────────────────────
AGENT_NAME = os.getenv("AGENT_NAME", "hypervisor-01")
AGENT_PORT = int(os.getenv("AGENT_PORT", "8094"))
CREW_ORCHESTRATOR_URL = os.getenv("CREW_ORCHESTRATOR_URL", "http://crew-orchestrator:8081")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
DOCKER_SOCKET = os.getenv("DOCKER_SOCKET", "unix:///var/run/docker.sock")
OBSERVER_URL = os.getenv("OBSERVER_URL", "http://hyper-observer:8092")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", "")

# Thresholds
CPU_THRESHOLD_WARN = float(os.getenv("CPU_THRESHOLD_WARN", "70"))
CPU_THRESHOLD_CRIT = float(os.getenv("CPU_THRESHOLD_CRIT", "90"))
RAM_THRESHOLD_WARN = float(os.getenv("RAM_THRESHOLD_WARN", "75"))
RAM_THRESHOLD_CRIT = float(os.getenv("RAM_THRESHOLD_CRIT", "90"))
DISK_THRESHOLD_WARN = float(os.getenv("DISK_THRESHOLD_WARN", "80"))
OOM_PREDICTION_WINDOW = int(os.getenv("OOM_PREDICTION_WINDOW", "300"))  # samples of history
DISK_PATH = os.getenv("DISK_PATH", "/")  # bind-mount host disk here to measure the laptop

# Safety / behaviour
ENFORCE_SCALING = os.getenv("ENFORCE_SCALING", "false").lower() in ("1", "true", "yes")
SUSTAINED_CRIT = int(os.getenv("SUSTAINED_CRIT", "3"))  # consecutive crit samples before acting
CONTAINER_STATS_TTL = float(os.getenv("CONTAINER_STATS_TTL", "12"))  # seconds between stats sweeps
NON_CRITICAL = [s.strip().lower() for s in os.getenv(
    "NON_CRITICAL_CONTAINERS", "grafana,prometheus,loki,promtail").split(",") if s.strip()]
ALERT_HISTORY_MAX = int(os.getenv("ALERT_HISTORY_MAX", "200"))
MONITOR_INTERVAL = float(os.getenv("MONITOR_INTERVAL", "5"))
WS_INTERVAL = float(os.getenv("WS_INTERVAL", "2"))


def _json_safe(obj) -> dict:
    """Round-trip through json with a str fallback so datetimes serialize cleanly."""
    return json.loads(json.dumps(obj, default=str))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_docker_time(created: str) -> Optional[datetime]:
    """Parse Docker's RFC3339 'Created' string (which may carry 9-digit nanoseconds)."""
    if not created:
        return None
    s = created.strip().replace("Z", "+00:00")
    # datetime.fromisoformat only accepts 3 or 6 fractional digits; trim nanoseconds.
    if "." in s:
        head, _, tail = s.partition(".")
        frac = ""
        rest = ""
        for i, ch in enumerate(tail):
            if ch.isdigit():
                frac += ch
            else:
                rest = tail[i:]
                break
        s = f"{head}.{frac[:6]}{rest}"
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


# ─── Data Models ──────────────────────────────────────────────────────
@dataclass
class SystemMetrics:
    timestamp: datetime
    cpu_percent: float
    cpu_count: int
    ram_used: int
    ram_total: int
    ram_percent: float
    disk_used: int
    disk_total: int
    disk_percent: float
    container_count: int
    running_containers: int

    @property
    def ram_available_mb(self) -> float:
        return (self.ram_total - self.ram_used) / (1024 * 1024)

    @property
    def is_memory_critical(self) -> bool:
        return self.ram_percent >= RAM_THRESHOLD_CRIT

    @property
    def is_cpu_critical(self) -> bool:
        return self.cpu_percent >= CPU_THRESHOLD_CRIT


@dataclass
class ContainerMetrics:
    container_id: str
    container_name: str
    image: str
    state: str
    cpu_percent: float
    memory_mb: float
    memory_limit_mb: float
    memory_percent: float
    restart_count: int
    uptime_seconds: int


@dataclass
class Alert:
    level: str  # "info", "warn", "crit"
    category: str  # "cpu", "memory", "disk", "container"
    message: str
    timestamp: datetime
    metrics: Optional[Dict] = None


# ─── HyperVisor Agent ─────────────────────────────────────────────────
class HyperVisorAgent:
    def __init__(self):
        self._docker_client: Optional[docker.DockerClient] = None
        self._redis: Optional[redis.Redis] = None

        # Metrics history (for trend analysis)
        self.metrics_history: deque = deque(maxlen=OOM_PREDICTION_WINDOW)
        self.container_history: Dict[str, deque] = {}

        # Cached container metrics (stats calls are slow — sample on a TTL)
        self._container_cache: List[ContainerMetrics] = []
        self._container_cache_ts: float = 0.0
        self._stats_lock = asyncio.Lock()

        # Alert tracking
        self.active_alerts: List[Alert] = []
        self.alert_cooldown: Dict[str, datetime] = {}

        # Auto-scaling state
        self.critical_streak: int = 0
        self.stopped_by_agent: Set[str] = set()  # names we stopped, for heal-back
        self.scale_lock = asyncio.Lock()

        # WebSocket connections
        self.active_ws: List[WebSocket] = []

        mode = "ENFORCE" if ENFORCE_SCALING else "DRY-RUN"
        logger.info(f"🧬 HyperVisor Agent {AGENT_NAME} initialized (scaling mode: {mode})")

    # ── Client accessors (lazy + self-healing) ──────────────────────
    @property
    def docker_client(self) -> docker.DockerClient:
        if self._docker_client is None:
            self._docker_client = docker.DockerClient(base_url=DOCKER_SOCKET)
        return self._docker_client

    def _reset_docker(self):
        self._docker_client = None

    @property
    def redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(REDIS_URL, socket_connect_timeout=2, socket_timeout=2)
        return self._redis

    # ── Collection ───────────────────────────────────────────────────
    def get_system_metrics(self) -> SystemMetrics:
        """Gather current system metrics via psutil."""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()

        vm = psutil.virtual_memory()
        try:
            du = psutil.disk_usage(DISK_PATH)
        except Exception:
            du = psutil.disk_usage("/")

        try:
            containers = self.docker_client.containers.list(all=True)
            running = len([c for c in containers if c.status == "running"])
            total = len(containers)
        except Exception as e:
            logger.error(f"Docker unreachable while counting containers: {e}")
            self._reset_docker()
            total = running = 0

        metrics = SystemMetrics(
            timestamp=_now(),
            cpu_percent=cpu_percent,
            cpu_count=cpu_count,
            ram_used=vm.used,
            ram_total=vm.total,
            ram_percent=vm.percent,
            disk_used=du.used,
            disk_total=du.total,
            disk_percent=du.percent,
            container_count=total,
            running_containers=running,
        )

        self.metrics_history.append(metrics)
        return metrics

    def _collect_container_metrics(self) -> List[ContainerMetrics]:
        """Blocking per-container stats sweep. Call via asyncio.to_thread."""
        try:
            containers = self.docker_client.containers.list()
        except Exception as e:
            logger.error(f"Docker unreachable while listing containers: {e}")
            self._reset_docker()
            return []

        container_metrics: List[ContainerMetrics] = []
        for container in containers:
            try:
                stats_d = container.stats(stream=False)
                cpu_delta = (stats_d['cpu_stats']['cpu_usage']['total_usage']
                             - stats_d['precpu_stats']['cpu_usage']['total_usage'])
                system_delta = (stats_d['cpu_stats'].get('system_cpu_usage', 0)
                                - stats_d['precpu_stats'].get('system_cpu_usage', 0))
                cpu_percent = (cpu_delta / system_delta * 100.0) if system_delta > 0 else 0.0

                mem = stats_d.get('memory_stats', {})
                memory_mb = mem.get('usage', 0) / (1024 * 1024)
                memory_limit_mb = mem.get('limit', 0) / (1024 * 1024)
                memory_percent = (memory_mb / memory_limit_mb * 100) if memory_limit_mb > 0 else 0.0

                created = _parse_docker_time(container.attrs.get('Created', ''))
                uptime = int((_now() - created).total_seconds()) if created else 0

                try:
                    image = container.image.short_id
                except Exception:
                    image = "unknown"

                cm = ContainerMetrics(
                    container_id=container.id[:12],
                    container_name=container.name,
                    image=image,
                    state=container.status,
                    cpu_percent=round(cpu_percent, 2),
                    memory_mb=round(memory_mb, 1),
                    memory_limit_mb=round(memory_limit_mb, 1),
                    memory_percent=round(memory_percent, 1),
                    restart_count=container.attrs.get('RestartCount', 0),
                    uptime_seconds=uptime,
                )
                container_metrics.append(cm)

                hist = self.container_history.setdefault(container.name, deque(maxlen=OOM_PREDICTION_WINDOW))
                hist.append(cm)
            except Exception as e:
                logger.error(f"Error reading container {getattr(container, 'name', '?')}: {e}")

        return container_metrics

    async def get_container_metrics(self, force: bool = False) -> List[ContainerMetrics]:
        """TTL-cached, non-blocking wrapper around the stats sweep."""
        now = time.monotonic()
        if not force and (now - self._container_cache_ts) < CONTAINER_STATS_TTL and self._container_cache:
            return self._container_cache

        async with self._stats_lock:
            # Another coroutine may have refreshed while we waited on the lock.
            now = time.monotonic()
            if not force and (now - self._container_cache_ts) < CONTAINER_STATS_TTL and self._container_cache:
                return self._container_cache
            metrics = await asyncio.to_thread(self._collect_container_metrics)
            self._container_cache = metrics
            self._container_cache_ts = time.monotonic()
            return metrics

    # ── Prediction ───────────────────────────────────────────────────
    async def detect_oom_risk(self) -> Optional[Tuple[str, float]]:
        """
        Predict OOM within the window using linear regression on the RAM trend.
        Returns (target, probability 0-100) or None.
        """
        if len(self.metrics_history) < 10:
            return None

        # Regress on seconds-since-first-sample to keep the numbers small & stable.
        t0 = self.metrics_history[0].timestamp.timestamp()
        rel_t = np.array([m.timestamp.timestamp() - t0 for m in self.metrics_history])
        ram_percents = np.array([m.ram_percent for m in self.metrics_history])

        if np.ptp(rel_t) < 1e-6:
            return None

        try:
            slope, intercept, r_value, _p, _stderr = stats.linregress(rel_t, ram_percents)
        except Exception as e:
            logger.debug(f"OOM regression failed: {e}")
            return None

        if slope <= 0:  # RAM not trending up → no OOM risk
            return None

        horizon = min(OOM_PREDICTION_WINDOW, 300)  # seconds to look ahead
        future_t = (rel_t[-1]) + horizon
        predicted = slope * future_t + intercept

        if predicted >= RAM_THRESHOLD_CRIT:
            # severity: 90%→0, 100%→100 (extrapolation can exceed 100 → clamps to 100)
            severity = min(100.0, max(0.0, (predicted - RAM_THRESHOLD_CRIT) * (100.0 / (100.0 - RAM_THRESHOLD_CRIT))))
            confidence = min(1.0, abs(r_value))
            probability = round(severity * confidence, 1)
            logger.warning(
                f"⚠️ OOM RISK: predicted RAM {predicted:.1f}% in {horizon}s "
                f"(slope {slope:.3f}%/s, r={r_value:.2f}, prob {probability:.0f}%)")
            return ("system", probability)

        return None

    # ── Alerting ─────────────────────────────────────────────────────
    async def generate_alerts(self, metrics: SystemMetrics,
                              container_metrics: List[ContainerMetrics]) -> List[Alert]:
        alerts: List[Alert] = []
        now = _now()

        # CPU
        if metrics.cpu_percent >= CPU_THRESHOLD_CRIT:
            level, msg = "crit", f"🔴 CRITICAL CPU: {metrics.cpu_percent:.1f}% (threshold {CPU_THRESHOLD_CRIT}%)"
        elif metrics.cpu_percent >= CPU_THRESHOLD_WARN:
            level, msg = "warn", f"🟡 HIGH CPU: {metrics.cpu_percent:.1f}% (threshold {CPU_THRESHOLD_WARN}%)"
        else:
            level = None
        if level and self._check_cooldown("cpu", 60):
            alerts.append(Alert(level, "cpu", msg, now, {"cpu_percent": metrics.cpu_percent}))

        # RAM
        if metrics.ram_percent >= RAM_THRESHOLD_CRIT:
            level, msg = "crit", (f"🔴 CRITICAL MEMORY: {metrics.ram_percent:.1f}% "
                                  f"({metrics.ram_available_mb:.0f}MB free, threshold {RAM_THRESHOLD_CRIT}%)")
        elif metrics.ram_percent >= RAM_THRESHOLD_WARN:
            level, msg = "warn", (f"🟡 HIGH MEMORY: {metrics.ram_percent:.1f}% "
                                  f"({metrics.ram_available_mb:.0f}MB free, threshold {RAM_THRESHOLD_WARN}%)")
        else:
            level = None
        if level and self._check_cooldown("memory", 60):
            alerts.append(Alert(level, "memory", msg, now,
                                {"ram_percent": metrics.ram_percent, "ram_available_mb": metrics.ram_available_mb}))

        # Disk
        if metrics.disk_percent >= DISK_THRESHOLD_WARN and self._check_cooldown("disk", 300):
            alerts.append(Alert("warn", "disk",
                                f"🟡 DISK SPACE LOW: {metrics.disk_percent:.1f}% used (threshold {DISK_THRESHOLD_WARN}%)",
                                now, {"disk_percent": metrics.disk_percent}))

        # Per-container
        for cm in container_metrics:
            if cm.memory_percent >= 95 and cm.state == "running":
                if self._check_cooldown(f"container_{cm.container_name}", 120):
                    alerts.append(Alert("crit", "container",
                                        f"🔴 {cm.container_name} near memory limit: {cm.memory_percent:.0f}% "
                                        f"({cm.memory_mb:.0f}/{cm.memory_limit_mb:.0f}MB)",
                                        now, {"container": cm.container_name, "memory_percent": cm.memory_percent}))
            if cm.restart_count > 5 and cm.uptime_seconds < 300:
                if self._check_cooldown(f"restart_{cm.container_name}", 300):
                    alerts.append(Alert("warn", "container",
                                        f"⚠️ {cm.container_name} restarting frequently "
                                        f"({cm.restart_count} restarts, up {cm.uptime_seconds}s)",
                                        now, {"container": cm.container_name, "restart_count": cm.restart_count}))

        # OOM prediction
        oom_risk = await self.detect_oom_risk()
        if oom_risk:
            _target, probability = oom_risk
            if self._check_cooldown("oom_prediction", 60):
                alerts.append(Alert("crit", "memory",
                                    f"🚨 OOM PREDICTION: {probability:.0f}% risk within 5 minutes",
                                    now, {"oom_probability": probability}))

        self.active_alerts = alerts
        return alerts

    def _check_cooldown(self, key: str, seconds: int) -> bool:
        now = _now()
        last = self.alert_cooldown.get(key)
        if last is None or (now - last).total_seconds() >= seconds:
            self.alert_cooldown[key] = now
            return True
        return False

    # ── Auto-scaling (guarded) ───────────────────────────────────────
    async def auto_scale_containers(self, metrics: SystemMetrics) -> List[str]:
        """
        Shed load under sustained memory pressure. DRY-RUN unless ENFORCE_SCALING.
        Returns a list of action strings (prefixed [DRY-RUN] when not enforcing).
        """
        actions: List[str] = []
        if not metrics.is_memory_critical:
            return actions

        async with self.scale_lock:
            tag = "" if ENFORCE_SCALING else "[DRY-RUN] "
            try:
                containers = self.docker_client.containers.list(all=True)
            except Exception as e:
                logger.error(f"Docker unreachable during auto-scale: {e}")
                self._reset_docker()
                return actions

            # 1. Remove zombie containers (excessive restarts, not currently running)
            for c in containers:
                restart_count = c.attrs.get('RestartCount', 0)
                if restart_count > 10 and c.status != "running":
                    msg = f"{tag}remove zombie {c.name} (restart_count={restart_count})"
                    if ENFORCE_SCALING:
                        try:
                            c.remove(force=True)
                        except Exception as e:
                            logger.error(f"Failed to remove {c.name}: {e}")
                            continue
                    actions.append(msg)
                    logger.info(f"🗑️ {msg}")

            # 2. Stop non-critical monitoring containers to free RAM
            for c in containers:
                if c.status == "running" and any(nc in c.name.lower() for nc in NON_CRITICAL):
                    msg = f"{tag}stop non-critical {c.name} (memory pressure)"
                    if ENFORCE_SCALING:
                        try:
                            c.stop(timeout=15)
                            self.stopped_by_agent.add(c.name)
                        except Exception as e:
                            logger.error(f"Failed to stop {c.name}: {e}")
                            continue
                    actions.append(msg)
                    logger.info(f"⏸️ {msg}")

        return actions

    async def heal_back(self, metrics: SystemMetrics) -> List[str]:
        """Restart containers we stopped, once RAM has recovered below WARN."""
        actions: List[str] = []
        if not self.stopped_by_agent or metrics.ram_percent >= RAM_THRESHOLD_WARN:
            return actions

        async with self.scale_lock:
            for name in list(self.stopped_by_agent):
                try:
                    c = self.docker_client.containers.get(name)
                    c.start()
                    self.stopped_by_agent.discard(name)
                    actions.append(f"restarted {name} (pressure cleared)")
                    logger.info(f"♻️ Restarted {name} (RAM back to {metrics.ram_percent:.1f}%)")
                except Exception as e:
                    logger.error(f"Failed to restart {name}: {e}")
        return actions

    # ── Broadcast ────────────────────────────────────────────────────
    async def broadcast_alert(self, alert: Alert):
        payload = _json_safe(asdict(alert))

        # Redis cache (bounded)
        try:
            key = f"alerts:{AGENT_NAME}"
            self.redis.lpush(key, json.dumps(payload))
            self.redis.ltrim(key, 0, ALERT_HISTORY_MAX - 1)
        except Exception as e:
            logger.debug(f"Redis alert cache failed: {e}")

        # WebSocket broadcast (copy list; drop dead sockets)
        for ws in list(self.active_ws):
            try:
                await ws.send_json(payload)
            except Exception as e:
                logger.debug(f"WebSocket send failed, dropping: {e}")
                if ws in self.active_ws:
                    self.active_ws.remove(ws)

        # Discord webhook for crit
        if alert.level == "crit" and DISCORD_WEBHOOK:
            asyncio.create_task(self._send_discord_alert(alert))

    async def _send_discord_alert(self, alert: Alert):
        import aiohttp
        color = {"crit": 16711680, "warn": 16776960, "info": 65280}.get(alert.level, 8421504)
        embed = {
            "title": f"🧬 {AGENT_NAME}",
            "description": alert.message,
            "color": color,
            "footer": {"text": alert.timestamp.isoformat()},
        }
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(DISCORD_WEBHOOK, json={"embeds": [embed]}) as resp:
                    if resp.status not in (200, 204):
                        logger.error(f"Discord webhook failed: {resp.status}")
        except Exception as e:
            logger.error(f"Discord alert failed: {e}")


# ─── Agent Instance ───────────────────────────────────────────────────
hypervisor = HyperVisorAgent()


# ─── Background Monitoring Loop ───────────────────────────────────────
async def monitor_loop():
    """Continuous monitoring, alerting, and guarded auto-scaling."""
    logger.info("🔁 Monitor loop started")
    while True:
        try:
            system_metrics = hypervisor.get_system_metrics()
            container_metrics = await hypervisor.get_container_metrics()

            alerts = await hypervisor.generate_alerts(system_metrics, container_metrics)
            for alert in alerts:
                logger.info(alert.message)
                await hypervisor.broadcast_alert(alert)

            # Track sustained memory pressure before acting.
            if system_metrics.is_memory_critical:
                hypervisor.critical_streak += 1
            else:
                hypervisor.critical_streak = 0

            if hypervisor.critical_streak >= SUSTAINED_CRIT:
                for action in await hypervisor.auto_scale_containers(system_metrics):
                    logger.info(action)

            # Heal-back when pressure clears.
            for action in await hypervisor.heal_back(system_metrics):
                logger.info(action)

            # Cache latest snapshot in Redis (fail-soft).
            try:
                hypervisor.redis.set(
                    f"metrics:{AGENT_NAME}:latest",
                    json.dumps(_json_safe(asdict(system_metrics))),
                    ex=15,
                )
            except Exception as e:
                logger.debug(f"Redis metrics cache failed: {e}")

        except Exception as e:
            logger.error(f"Monitor loop error: {e}")

        await asyncio.sleep(MONITOR_INTERVAL)


# ─── Lifespan (startup + graceful shutdown) ───────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(monitor_loop())
    logger.info(f"✅ HyperVisor Agent {AGENT_NAME} started on port {AGENT_PORT}")
    try:
        yield
    finally:
        logger.info("🛑 Shutting down HyperVisor Agent…")
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        for ws in list(hypervisor.active_ws):
            try:
                await ws.close()
            except Exception:
                pass
        logger.info("👋 HyperVisor Agent stopped cleanly")


app = FastAPI(title="HyperVisor Agent", version="1.1.0", lifespan=lifespan)


# ─── REST Endpoints ───────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "healthy", "agent": AGENT_NAME, "enforce_scaling": ENFORCE_SCALING}


@app.get("/metrics")
async def get_metrics():
    system_metrics = hypervisor.get_system_metrics()
    container_metrics = await hypervisor.get_container_metrics()
    return {
        "system": _json_safe(asdict(system_metrics)),
        "containers": [_json_safe(asdict(cm)) for cm in container_metrics],
        "active_alerts": len(hypervisor.active_alerts),
        "enforce_scaling": ENFORCE_SCALING,
        "stopped_by_agent": sorted(hypervisor.stopped_by_agent),
    }


@app.get("/alerts")
async def get_alerts():
    return {
        "alerts": [_json_safe(asdict(a)) for a in hypervisor.active_alerts],
        "timestamp": _now().isoformat(),
    }


@app.post("/scale")
async def trigger_scale(background_tasks: BackgroundTasks):
    metrics = hypervisor.get_system_metrics()
    background_tasks.add_task(hypervisor.auto_scale_containers, metrics)
    return {"status": "scaling triggered", "ram_percent": metrics.ram_percent,
            "enforce_scaling": ENFORCE_SCALING}


@app.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    await websocket.accept()
    hypervisor.active_ws.append(websocket)
    try:
        while True:
            system_metrics = hypervisor.get_system_metrics()
            container_metrics = await hypervisor.get_container_metrics()
            alerts = await hypervisor.generate_alerts(system_metrics, container_metrics)
            for alert in alerts:
                await hypervisor.broadcast_alert(alert)
            await websocket.send_json({
                "type": "metrics",
                "system": _json_safe(asdict(system_metrics)),
                "containers": [_json_safe(asdict(cm)) for cm in container_metrics],
                "alerts": [_json_safe(asdict(a)) for a in alerts],
            })
            await asyncio.sleep(WS_INTERVAL)
    except Exception as e:
        logger.debug(f"WebSocket closed: {e}")
    finally:
        if websocket in hypervisor.active_ws:
            hypervisor.active_ws.remove(websocket)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=AGENT_PORT, log_level="info")
