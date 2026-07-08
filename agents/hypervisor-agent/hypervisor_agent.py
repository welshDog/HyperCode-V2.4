"""
🧬 HYPERVISOR AGENT — Real-Time Resource Guardian for HyperFocus Z0ne

Monitors laptop CPU/RAM/disk, auto-scales containers, predicts OOM, 
and keeps your distributed system breathing.

Features:
  - Live metrics streaming (WebSocket + REST)
  - Predictive OOM detection (ML-based trend analysis)
  - Auto-scaling rules (kill zombie containers, redistribute load)
  - Crew Orchestrator integration + Redis cache
  - Discord alerts (broski-bot)
  - MCP bridge for CLI commands
"""

import asyncio
import json
import logging
import os
import psutil
import docker
import redis
from datetime import datetime, timedelta
from collections import deque
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from fastapi import FastAPI, WebSocket, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import numpy as np
from scipy import stats
import uvicorn

# ─── Setup ────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="HyperVisor Agent", version="1.0.0")

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
OOM_PREDICTION_WINDOW = int(os.getenv("OOM_PREDICTION_WINDOW", "300"))  # seconds

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
        self.docker_client = docker.DockerClient(base_url=DOCKER_SOCKET)
        self.redis = redis.from_url(REDIS_URL)
        
        # Metrics history (for trend analysis)
        self.metrics_history = deque(maxlen=OOM_PREDICTION_WINDOW)
        self.container_history: Dict[str, deque] = {}
        
        # Alert tracking
        self.active_alerts: List[Alert] = []
        self.alert_cooldown: Dict[str, datetime] = {}
        
        # WebSocket connections
        self.active_ws: List[WebSocket] = []
        
        logger.info(f"🧬 HyperVisor Agent {AGENT_NAME} initialized")
    
    def get_system_metrics(self) -> SystemMetrics:
        """Gather current system metrics via psutil."""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()
        
        vm = psutil.virtual_memory()
        sm = psutil.disk_usage('/')
        
        containers = self.docker_client.containers.list(all=True)
        running = len([c for c in containers if c.status == "running"])
        
        metrics = SystemMetrics(
            timestamp=datetime.utcnow(),
            cpu_percent=cpu_percent,
            cpu_count=cpu_count,
            ram_used=vm.used,
            ram_total=vm.total,
            ram_percent=vm.percent,
            disk_used=sm.used,
            disk_total=sm.total,
            disk_percent=sm.percent,
            container_count=len(containers),
            running_containers=running,
        )
        
        self.metrics_history.append(metrics)
        return metrics
    
    def get_container_metrics(self) -> List[ContainerMetrics]:
        """Get per-container resource usage."""
        containers = self.docker_client.containers.list()
        container_metrics = []
        
        for container in containers:
            try:
                stats = container.stats(stream=False)
                cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                           stats['precpu_stats']['cpu_usage']['total_usage']
                system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                              stats['precpu_stats']['system_cpu_usage']
                cpu_percent = (cpu_delta / system_delta * 100.0) if system_delta > 0 else 0
                
                memory_mb = stats['memory_stats'].get('usage', 0) / (1024 * 1024)
                memory_limit_mb = stats['memory_stats'].get('limit', 0) / (1024 * 1024)
                memory_percent = (memory_mb / memory_limit_mb * 100) if memory_limit_mb > 0 else 0
                
                created = container.attrs['Created']
                uptime = (datetime.utcnow() - datetime.fromisoformat(created.replace('Z', '+00:00'))).total_seconds()
                
                cm = ContainerMetrics(
                    container_id=container.id[:12],
                    container_name=container.name,
                    image=container.image.short_id,
                    state=container.status,
                    cpu_percent=cpu_percent,
                    memory_mb=memory_mb,
                    memory_limit_mb=memory_limit_mb,
                    memory_percent=memory_percent,
                    restart_count=container.attrs['RestartCount'],
                    uptime_seconds=int(uptime),
                )
                container_metrics.append(cm)
                
                # Track history
                if container.name not in self.container_history:
                    self.container_history[container.name] = deque(maxlen=OOM_PREDICTION_WINDOW)
                self.container_history[container.name].append(cm)
            
            except Exception as e:
                logger.error(f"Error reading container {container.name}: {e}")
        
        return container_metrics
    
    async def detect_oom_risk(self) -> Optional[Tuple[str, float]]:
        """
        Predict OOM in next 5 minutes using linear regression on RAM trend.
        Returns: (container_name, predicted_oom_probability) or None
        """
        if len(self.metrics_history) < 10:
            return None
        
        # System-level OOM prediction
        timestamps = np.array([m.timestamp.timestamp() for m in self.metrics_history])
        ram_percents = np.array([m.ram_percent for m in self.metrics_history])
        
        try:
            slope, intercept, r_value, p_value, std_err = stats.linregress(timestamps, ram_percents)
            
            # Predict RAM % in 5 minutes
            future_timestamp = (datetime.utcnow() + timedelta(seconds=300)).timestamp()
            predicted_ram_percent = slope * future_timestamp + intercept
            
            if predicted_ram_percent >= 95:
                oom_probability = min(100, (predicted_ram_percent - 90) * 2)
                logger.warning(f"⚠️ OOM RISK DETECTED: Predicted RAM {predicted_ram_percent:.1f}% in 5 min (prob: {oom_probability:.0f}%)")
                return ("system", oom_probability)
        
        except Exception as e:
            logger.debug(f"OOM prediction failed: {e}")
        
        return None
    
    async def generate_alerts(self, metrics: SystemMetrics, container_metrics: List[ContainerMetrics]) -> List[Alert]:
        """Generate alerts based on thresholds and trends."""
        alerts = []
        now = datetime.utcnow()
        
        # CPU alert
        if metrics.cpu_percent >= CPU_THRESHOLD_CRIT:
            level = "crit"
            category = "cpu"
            msg = f"🔴 CRITICAL CPU: {metrics.cpu_percent:.1f}% (threshold: {CPU_THRESHOLD_CRIT}%)"
        elif metrics.cpu_percent >= CPU_THRESHOLD_WARN:
            level = "warn"
            category = "cpu"
            msg = f"🟡 HIGH CPU: {metrics.cpu_percent:.1f}% (threshold: {CPU_THRESHOLD_WARN}%)"
        else:
            level = None
        
        if level and self._check_cooldown(category, 60):
            alerts.append(Alert(level=level, category=category, message=msg, timestamp=now, 
                               metrics={"cpu_percent": metrics.cpu_percent}))
        
        # RAM alert
        if metrics.ram_percent >= RAM_THRESHOLD_CRIT:
            level = "crit"
            category = "memory"
            msg = f"🔴 CRITICAL MEMORY: {metrics.ram_percent:.1f}% ({metrics.ram_available_mb:.0f}MB free) (threshold: {RAM_THRESHOLD_CRIT}%)"
        elif metrics.ram_percent >= RAM_THRESHOLD_WARN:
            level = "warn"
            category = "memory"
            msg = f"🟡 HIGH MEMORY: {metrics.ram_percent:.1f}% ({metrics.ram_available_mb:.0f}MB free) (threshold: {RAM_THRESHOLD_WARN}%)"
        else:
            level = None
        
        if level and self._check_cooldown(category, 60):
            alerts.append(Alert(level=level, category=category, message=msg, timestamp=now,
                               metrics={"ram_percent": metrics.ram_percent, "ram_available_mb": metrics.ram_available_mb}))
        
        # Disk alert
        if metrics.disk_percent >= DISK_THRESHOLD_WARN:
            level = "warn"
            category = "disk"
            msg = f"🟡 DISK SPACE LOW: {metrics.disk_percent:.1f}% used (threshold: {DISK_THRESHOLD_WARN}%)"
            if self._check_cooldown(category, 300):
                alerts.append(Alert(level=level, category=category, message=msg, timestamp=now,
                                   metrics={"disk_percent": metrics.disk_percent}))
        
        # Container-level alerts
        for cm in container_metrics:
            if cm.memory_percent >= 95 and cm.state == "running":
                msg = f"🔴 {cm.container_name} near memory limit: {cm.memory_percent:.0f}% ({cm.memory_mb:.0f}MB / {cm.memory_limit_mb:.0f}MB)"
                if self._check_cooldown(f"container_{cm.container_name}", 120):
                    alerts.append(Alert(level="crit", category="container", message=msg, timestamp=now,
                                       metrics={"container": cm.container_name, "memory_percent": cm.memory_percent}))
            
            if cm.restart_count > 5 and cm.uptime_seconds < 300:
                msg = f"⚠️ {cm.container_name} restarting frequently ({cm.restart_count} restarts in {cm.uptime_seconds}s)"
                if self._check_cooldown(f"restart_{cm.container_name}", 300):
                    alerts.append(Alert(level="warn", category="container", message=msg, timestamp=now,
                                       metrics={"container": cm.container_name, "restart_count": cm.restart_count}))
        
        # OOM prediction
        oom_risk = await self.detect_oom_risk()
        if oom_risk:
            target, probability = oom_risk
            msg = f"🚨 OOM PREDICTION: {probability:.0f}% risk in 5 minutes"
            if self._check_cooldown("oom_prediction", 60):
                alerts.append(Alert(level="crit", category="memory", message=msg, timestamp=now,
                                   metrics={"oom_probability": probability}))
        
        self.active_alerts = alerts
        return alerts
    
    def _check_cooldown(self, key: str, seconds: int) -> bool:
        """Check if enough time has passed since last alert of this type."""
        now = datetime.utcnow()
        if key not in self.alert_cooldown:
            self.alert_cooldown[key] = now
            return True
        
        if (now - self.alert_cooldown[key]).total_seconds() >= seconds:
            self.alert_cooldown[key] = now
            return True
        
        return False
    
    async def auto_scale_containers(self, metrics: SystemMetrics) -> List[str]:
        """Apply auto-scaling rules: kill zombies, restart stalled services."""
        actions = []
        
        if metrics.is_memory_critical:
            containers = self.docker_client.containers.list()
            
            # 1. Kill zombie containers (restarting excessively)
            for c in containers:
                restart_count = c.attrs['RestartCount']
                state = c.status
                
                if restart_count > 10 and state != "running":
                    try:
                        c.stop()
                        c.remove()
                        actions.append(f"Killed zombie container: {c.name} (restart_count={restart_count})")
                        logger.info(f"🗑️ Removed {c.name} (zombie, {restart_count} restarts)")
                    except Exception as e:
                        logger.error(f"Failed to remove {c.name}: {e}")
            
            # 2. Stop non-critical monitoring containers
            non_critical = ["grafana", "prometheus", "loki", "promtail"]
            for c in containers:
                if c.status == "running" and any(nc in c.name.lower() for nc in non_critical):
                    try:
                        c.stop()
                        actions.append(f"Stopped non-critical container: {c.name}")
                        logger.info(f"⏸️ Stopped {c.name} (memory pressure)")
                    except Exception as e:
                        logger.error(f"Failed to stop {c.name}: {e}")
        
        return actions
    
    async def broadcast_alert(self, alert: Alert):
        """Send alert to Redis, Discord, and connected WebSockets."""
        # Redis cache
        self.redis.lpush(f"alerts:{AGENT_NAME}", json.dumps(asdict(alert), default=str))
        
        # WebSocket broadcast
        for ws in self.active_ws:
            try:
                await ws.send_json(asdict(alert), default=str)
            except Exception as e:
                logger.error(f"WebSocket send failed: {e}")
        
        # Discord webhook
        if alert.level == "crit" and DISCORD_WEBHOOK:
            asyncio.create_task(self._send_discord_alert(alert))
    
    async def _send_discord_alert(self, alert: Alert):
        """Send alert to Discord via webhook."""
        import aiohttp
        
        color = {"crit": 16711680, "warn": 16776960, "info": 65280}[alert.level]
        embed = {
            "title": f"🧬 {AGENT_NAME}",
            "description": alert.message,
            "color": color,
            "footer": {"text": alert.timestamp.isoformat()},
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(DISCORD_WEBHOOK, json={"embeds": [embed]}) as resp:
                    if resp.status != 204:
                        logger.error(f"Discord webhook failed: {resp.status}")
        except Exception as e:
            logger.error(f"Discord alert failed: {e}")


# ─── Agent Instance ───────────────────────────────────────────────────
hypervisor = HyperVisorAgent()


# ─── REST Endpoints ───────────────────────────────────────────────────
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "agent": AGENT_NAME}


@app.get("/metrics")
async def get_metrics():
    """Return current system and container metrics."""
    system_metrics = hypervisor.get_system_metrics()
    container_metrics = hypervisor.get_container_metrics()
    
    return {
        "system": asdict(system_metrics),
        "containers": [asdict(cm) for cm in container_metrics],
        "active_alerts": len(hypervisor.active_alerts),
    }


@app.get("/alerts")
async def get_alerts():
    """Return recent alerts."""
    return {
        "alerts": [asdict(a) for a in hypervisor.active_alerts],
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/scale")
async def trigger_scale(background_tasks: BackgroundTasks):
    """Manually trigger auto-scaling."""
    metrics = hypervisor.get_system_metrics()
    background_tasks.add_task(hypervisor.auto_scale_containers, metrics)
    return {"status": "scaling triggered", "ram_percent": metrics.ram_percent}


@app.websocket("/ws/metrics")
async def websocket_metrics(websocket: WebSocket):
    """WebSocket: Real-time metrics stream."""
    await websocket.accept()
    hypervisor.active_ws.append(websocket)
    
    try:
        while True:
            system_metrics = hypervisor.get_system_metrics()
            container_metrics = hypervisor.get_container_metrics()
            alerts = await hypervisor.generate_alerts(system_metrics, container_metrics)
            
            # Broadcast alerts
            for alert in alerts:
                await hypervisor.broadcast_alert(alert)
            
            payload = {
                "type": "metrics",
                "system": asdict(system_metrics),
                "containers": [asdict(cm) for cm in container_metrics],
                "alerts": [asdict(a) for a in alerts],
            }
            await websocket.send_json(payload, default=str)
            
            await asyncio.sleep(2)  # Update every 2 seconds
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    
    finally:
        hypervisor.active_ws.remove(websocket)


# ─── Background Monitoring Loop ───────────────────────────────────────
async def monitor_loop():
    """Continuous monitoring and auto-scaling."""
    while True:
        try:
            system_metrics = hypervisor.get_system_metrics()
            container_metrics = hypervisor.get_container_metrics()
            
            # Generate alerts
            alerts = await hypervisor.generate_alerts(system_metrics, container_metrics)
            for alert in alerts:
                logger.info(alert.message)
                await hypervisor.broadcast_alert(alert)
            
            # Auto-scale if critical
            if system_metrics.is_memory_critical or system_metrics.is_cpu_critical:
                actions = await hypervisor.auto_scale_containers(system_metrics)
                for action in actions:
                    logger.info(action)
            
            # Cache in Redis
            hypervisor.redis.set(
                f"metrics:{AGENT_NAME}:latest",
                json.dumps(asdict(system_metrics), default=str),
                ex=10
            )
        
        except Exception as e:
            logger.error(f"Monitor loop error: {e}")
        
        await asyncio.sleep(5)


@app.on_event("startup")
async def startup():
    """Start background monitoring on app startup."""
    asyncio.create_task(monitor_loop())
    logger.info(f"✅ HyperVisor Agent {AGENT_NAME} started on port {AGENT_PORT}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=AGENT_PORT, log_level="info")
