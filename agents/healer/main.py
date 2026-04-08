# ✅ STDLIB — complete clean import block
import asyncio
import json
import logging
import os
import sys
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional
from urllib.parse import urlparse

# 📍 Ensure /app/healer is on sys.path for absolute imports of mape_k_* modules
sys.path.insert(0, os.path.dirname(__file__))

# Third party
import httpx
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Local (relative imports for files in the same package)
from .adapters.docker_adapter import DockerAdapter
from .metrics import init_metrics
from .models import HealResult, HealerException, HealRequest

# │ Phase 3 — Event Bus wiring │
from agents.shared.agent_message import HealEvent, AgentMessage
from agents.shared.event_bus import AgentEventBus

# ── MAPE-K imports (absolute — resolved via sys.path above) ────────────────────────────────────
from mape_k_api import router as mape_k_router
from mape_k_engine import KnowledgeBase, mape_k_loop, DEFAULT_SERVICES
from mape_k_api import set_knowledge_base

# ── Logging ────────────────────────────────────────────────────────────────────────────────────
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level_name": record.levelname,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger("healer.main")
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# ── Config ────────────────────────────────────────────────────────────────────────────────────
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://crew-orchestrator:8080")
WATCHDOG_ENABLED = os.getenv("HEALER_WATCHDOG_ENABLED", "false").strip().lower() == "true"
WATCHDOG_INTERVAL_SECONDS = float(os.getenv("HEALER_WATCHDOG_INTERVAL_SECONDS", "60").strip() or "60")
WATCHDOG_SMOKE_API_KEY = os.getenv("HEALER_SMOKE_API_KEY", "").strip()
WATCHDOG_ORCHESTRATOR_API_KEY = os.getenv("HEALER_ORCHESTRATOR_API_KEY", "").strip()
WATCHDOG_AGENT = os.getenv("HEALER_WATCHDOG_AGENT", "").strip()
WATCHDOG_FORCE_RESTART = os.getenv("HEALER_WATCHDOG_FORCE_RESTART", "false").strip().lower() == "true"
HEALER_AGENT_ID = os.getenv("HEALER_AGENT_ID", "healer-01")

# ── Global state ───────────────────────────────────────────────────────────────────────────
redis_client: Optional[redis.Redis] = None
docker_adapter: Optional[DockerAdapter] = None
_throttle_paused_local: Dict[str, float] = {}
event_bus: Optional[AgentEventBus] = None  # │ Phase 3 │


# ── Models ────────────────────────────────────────────────────────────────────────────────────
class ThrottleStateUpdate(BaseModel):
    containers: List[str]
    paused: bool = True
    ttl_seconds: int = 900
    reason: Optional[str] = None


# ── Throttle helpers ──────────────────────────────────────────────────────────────────────────────
def _throttle_pause_key(container: str) -> str:
    return f"throttle:paused:{container}"


async def set_throttle_state(update: ThrottleStateUpdate) -> Dict[str, Any]:
    now = time.time()
    ttl = max(int(update.ttl_seconds), 10)
    applied: List[str] = []
    if redis_client:
        if update.paused:
            payload = json.dumps({"paused": True, "reason": update.reason, "until_ts": now + ttl})
            for c in update.containers:
                if not isinstance(c, str) or not c:
                    continue
                await redis_client.set(_throttle_pause_key(c), payload, ex=ttl)
                applied.append(c)
        else:
            keys = [_throttle_pause_key(c) for c in update.containers if isinstance(c, str) and c]
            if keys:
                await redis_client.delete(*keys)
                applied = [c for c in update.containers if isinstance(c, str) and c]
    else:
        if update.paused:
            until = now + ttl
            for c in update.containers:
                if not isinstance(c, str) or not c:
                    continue
                _throttle_paused_local[c] = until
                applied.append(c)
        else:
            for c in update.containers:
                if not isinstance(c, str) or not c:
                    continue
                _throttle_paused_local.pop(c, None)
                applied.append(c)
    return {"applied": applied, "paused": update.paused, "ttl_seconds": ttl}


async def is_throttle_paused(container: str) -> bool:
    if redis_client:
        value = await redis_client.get(_throttle_pause_key(container))
        return value is not None
    until = _throttle_paused_local.get(container)
    if until is None:
        return False
    if time.time() > until:
        _throttle_paused_local.pop(container, None)
        return False
    return True


async def get_throttle_state() -> Dict[str, Any]:
    if redis_client:
        keys = await redis_client.keys("throttle:paused:*")
        containers = [
            k.split("throttle:paused:", 1)[1]
            for k in keys
            if isinstance(k, str) and k.startswith("throttle:paused:")
        ]
        return {"containers": sorted(set(containers)), "backend": "redis"}
    now = time.time()
    containers = [c for c, until in _throttle_paused_local.items() if until > now]
    return {"containers": sorted(set(containers)), "backend": "memory"}


# ── Circuit Breaker ───────────────────────────────────────────────────────────────────────────────────
class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(self, failure_threshold=3, recovery_timeout=60):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.last_failure_time = None

    async def call(self, func: Callable[[], Coroutine[Any, Any, Any]]):
        if self.state == CircuitState.OPEN:
            if self.last_failure_time is None or (
                datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout)
            ):
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker: HALF_OPEN (testing recovery)")
            else:
                raise Exception("Circuit breaker is OPEN")
        try:
            result = await func()
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise e

    def on_success(self):
        if self.state != CircuitState.CLOSED:
            logger.info("Circuit breaker: CLOSED (recovered)")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.last_failure_time = None

    def on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        if self.failure_count >= self.failure_threshold:
            if self.state != CircuitState.OPEN:
                logger.warning(f"Circuit breaker: OPEN (failures: {self.failure_count})")
                self.state = CircuitState.OPEN


circuit_breakers: Dict[str, CircuitBreaker] = defaultdict(CircuitBreaker)


# ── Lifespan ────────────────────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client, docker_adapter, event_bus
    redis_client = await redis.from_url(REDIS_URL, decode_responses=True)
    docker_adapter = DockerAdapter(redis_url=REDIS_URL)

    # │ Phase 3 — Connect event bus │
    try:
        event_bus = AgentEventBus(REDIS_URL)
        await event_bus.connect()
        logger.info("✅ AgentEventBus connected - healer now publishing XP events")
    except Exception as e:
        logger.warning(f"⚠️  EventBus failed to connect (non-fatal): {e}")
        event_bus = None

    # 🧠 Start MAPE-K background loop
    kb = KnowledgeBase()
    set_knowledge_base(kb)
    asyncio.create_task(
        mape_k_loop(
            services=DEFAULT_SERVICES,
            kb=kb,
            interval_seconds=10,
        )
    )
    logger.info("🧠 MAPE-K loop started — polling every 10s")

    asyncio.create_task(alert_listener())
    asyncio.create_task(heartbeat_loop())
    if WATCHDOG_ENABLED:
        asyncio.create_task(watchdog_loop())
    logger.info("Healer Agent started - monitoring system health")
    yield
    if event_bus:
        await event_bus.disconnect()
    if redis_client:
        await redis_client.close()
    logger.info("Healer Agent shutting down")


# ── App ──────────────────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Healer Agent",
    version="0.3.0",
    description="Autonomous healing service for agents and systems",
    lifespan=lifespan,
)
init_metrics(app)

# 🧠 MAPE-K routes registered before app starts serving
app.include_router(mape_k_router)
logger.info("✅ MAPE-K API routes registered at /mape-k/*")


# ── Phase 3: Event bus publish helper ───────────────────────────────────────────────────────────
async def _publish_heal_event(
    healed_agent: str,
    heal_pattern: str,
    status: str,
    error_msg: Optional[str] = None,
) -> None:
    """Fire-and-forget publish to the event bus. Never crashes the healer."""
    if not event_bus:
        return
    try:
        xp    = 50  if status == "recovered" else 5
        coins = 10.0 if status == "recovered" else 1.0
        event = HealEvent(
            agent_id=HEALER_AGENT_ID,
            status="healing_success" if status == "recovered" else "failed",
            healed_agent_id=healed_agent,
            heal_pattern=heal_pattern,
            auto_resolved=True,
            xp_earned=xp,
            broski_coins=coins,
            error_trace=error_msg,
        )
        await event_bus.publish(event)
        await event_bus.award_xp(HEALER_AGENT_ID, xp=xp, coins=coins)
        logger.info(f"📤 HealEvent published | {event.summary()}")
    except Exception as e:
        logger.warning(f"EventBus publish failed (non-fatal): {e}")


# ── Heartbeat + heals_today ───────────────────────────────────────────────────────────────────────

def _seconds_until_midnight_utc() -> int:
    """Seconds from now until next midnight UTC — used to set heals_today expiry."""
    now = datetime.utcnow()
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return max(int((tomorrow - now).total_seconds()), 1)


async def heartbeat_loop() -> None:
    """
    Publishes agent heartbeat to Redis every 10s.
    Key: agents:heartbeat:healer-agent  (TTL 30s — disappears if healer dies)
    Also ensures healer:heals_today has a midnight-reset expiry.
    """
    key = f"agents:heartbeat:{HEALER_AGENT_ID}"
    while True:
        if redis_client:
            try:
                await redis_client.hset(
                    key,
                    mapping={
                        "name": "healer-agent",
                        "status": "online",
                        "last_seen": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    },
                )
                await redis_client.expire(key, 30)

                # Ensure healer:heals_today resets at midnight UTC
                ttl = await redis_client.ttl("healer:heals_today")
                if ttl == -1:  # key exists but has no expiry — set one
                    import calendar
                    midnight_ts = int(
                        (datetime.utcnow() + timedelta(seconds=_seconds_until_midnight_utc())).timestamp()
                    )
                    await redis_client.expireat("healer:heals_today", midnight_ts)
            except Exception as exc:
                logger.warning(f"Heartbeat write failed (non-fatal): {exc}")
        await asyncio.sleep(10)


# ── System helpers ────────────────────────────────────────────────────────────────────────────────
async def fetch_system_health() -> Dict[str, Dict[Any, Any]]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{ORCHESTRATOR_URL}/system/health")
            if r.status_code != 200:
                logger.error(f"Failed to fetch system health: {r.status_code}")
                return {}
            data = r.json()
            if isinstance(data, dict):
                return {str(k): v if isinstance(v, dict) else {} for k, v in data.items()}
            return {}
    except Exception as e:
        logger.error(f"Error fetching system health: {e}")
        return {}


async def fetch_agent_roster() -> Dict[str, str]:
    try:
        headers = {"Content-Type": "application/json"}
        if WATCHDOG_ORCHESTRATOR_API_KEY:
            headers["X-API-Key"] = WATCHDOG_ORCHESTRATOR_API_KEY
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{ORCHESTRATOR_URL}/agents", headers=headers)
            if r.status_code != 200:
                return {}
            data = r.json()
            if not isinstance(data, list):
                return {}
            roster: Dict[str, str] = {}
            for item in data:
                if not isinstance(item, dict):
                    continue
                agent_id = item.get("id")
                url = item.get("url")
                if isinstance(agent_id, str) and isinstance(url, str) and agent_id and url:
                    roster[agent_id] = url
            return roster
    except Exception:
        return {}


# ── Watchdog ──────────────────────────────────────────────────────────────────────────────────────
async def watchdog_cycle() -> None:
    if not WATCHDOG_SMOKE_API_KEY:
        return
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": WATCHDOG_SMOKE_API_KEY,
        "X-Smoke-Mode": "true",
    }
    roster = await fetch_agent_roster()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            payload: Dict[str, Any] = {"mode": "probe_health"}
            if WATCHDOG_AGENT:
                payload["agent"] = WATCHDOG_AGENT
            r = await client.post(f"{ORCHESTRATOR_URL}/execute/smoke", headers=headers, json=payload)
    except Exception:
        return
    if r.status_code != 200:
        return
    try:
        payload = r.json()
    except Exception:
        return
    agents = payload.get("agents")
    if not isinstance(agents, dict):
        return
    heal_tasks = []
    for agent_id, result in agents.items():
        if not isinstance(agent_id, str) or not isinstance(result, dict):
            continue
        status = result.get("status")
        if status not in {"unhealthy", "down"}:
            continue
        agent_url = roster.get(agent_id)
        if not agent_url:
            continue
        parsed = urlparse(agent_url)
        container_name = parsed.hostname or agent_id.replace("_", "-")
        logger.warning(f"Watchdog detected {agent_id}={status} -> healing {container_name}")
        heal_tasks.append(attempt_heal_agent(container_name, agent_url, attempts=2, timeout=5.0, force_restart=WATCHDOG_FORCE_RESTART))
    if not heal_tasks:
        return
    try:
        await asyncio.wait_for(asyncio.gather(*heal_tasks, return_exceptions=True), timeout=120.0)
    except Exception:
        return


async def watchdog_loop() -> None:
    if not WATCHDOG_SMOKE_API_KEY:
        logger.warning("Watchdog enabled but HEALER_SMOKE_API_KEY is not set")
    while True:
        try:
            await watchdog_cycle()
        except Exception:
            pass
        await asyncio.sleep(max(WATCHDOG_INTERVAL_SECONDS, 5.0))


# ── Healing logic ──────────────────────────────────────────────────────────────────────────────────
async def ping_agent_health(agent_url: str, timeout: float) -> bool:
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(f"{agent_url}/health")
            return r.status_code == 200
    except Exception as e:
        logger.debug(f"Health check failed for {agent_url}: {e}")
        return False


async def attempt_heal_agent(
    agent_name: str,
    agent_url: str,
    attempts: int,
    timeout: float,
    force_restart: bool = False,
) -> HealResult:
    breaker = circuit_breakers[agent_name]

    async def heal_task():
        if await is_throttle_paused(agent_name):
            raise HealerException(
                message="Healing paused by throttle",
                agent=agent_name,
                status="paused_by_throttle",
                details="Throttle Agent marked this container as intentionally paused",
            )
        logger.info(f"Checking health of {agent_name}...")
        healthy = await ping_agent_health(agent_url, timeout)
        if healthy:
            return HealResult(agent=agent_name, status="healthy", action="none", details="No action required", timestamp=datetime.now().isoformat())

        logger.warning(f"Agent {agent_name} is unhealthy. Attempting Docker restart...")
        if not docker_adapter:
            raise HealerException("Docker adapter unavailable", agent=agent_name, status="failed", details="Docker adapter not initialized")

        restarted = await docker_adapter.restart_container(agent_name, force=force_restart)
        if not restarted:
            raise HealerException("Docker restart command failed", agent=agent_name, status="failed", details="Docker restart command failed")

        for wait_time in [2, 5, 10]:
            await asyncio.sleep(wait_time)
            try:
                is_healthy = await asyncio.wait_for(ping_agent_health(agent_url, timeout), timeout=5.0)
                if is_healthy:
                    logger.info(f"✅ Agent {agent_name} recovered after {wait_time}s")
                    asyncio.create_task(_publish_heal_event(
                        healed_agent=agent_name,
                        heal_pattern="docker_restart",
                        status="recovered",
                    ))
                    # Increment daily heal counter — read by GET /api/v1/metrics
                    if redis_client:
                        try:
                            await redis_client.incr("healer:heals_today")
                            ttl = await redis_client.ttl("healer:heals_today")
                            if ttl < 0:  # set midnight expiry on first heal of the day
                                midnight_ts = int(
                                    (datetime.utcnow() + timedelta(seconds=_seconds_until_midnight_utc())).timestamp()
                                )
                                await redis_client.expireat("healer:heals_today", midnight_ts)
                        except Exception:
                            pass
                    return HealResult(agent=agent_name, status="recovered", action="restart", details=f"Restart successful - recovered after {wait_time}s", timestamp=datetime.now().isoformat())
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error checking {agent_name} health: {e}")
                continue

        raise HealerException("Agent unresponsive after restart", agent=agent_name, status="failed", details="Agent unresponsive after restart and multiple health checks")

    try:
        return await breaker.call(heal_task)
    except Exception as e:
        error_msg = str(e)
        asyncio.create_task(_publish_heal_event(
            healed_agent=agent_name,
            heal_pattern="docker_restart",
            status="failed",
            error_msg=error_msg,
        ))
        if isinstance(e, HealerException):
            return HealResult(agent=e.agent, status=e.status, action="none", details=e.details, timestamp=datetime.now().isoformat())
        return HealResult(
            agent=agent_name,
            status="circuit_open" if breaker.state == CircuitState.OPEN else "failed",
            action="none" if breaker.state == CircuitState.OPEN else "restart",
            details=error_msg,
            timestamp=datetime.now().isoformat(),
        )


async def auto_heal_all():
    logger.info("🔧 Auto-healing triggered by system alert")
    health_data = await fetch_system_health()
    if not health_data:
        logger.warning("No health data available - skipping healing cycle")
        return
    tasks = []
    for name, info in health_data.items():
        if info.get("status") == "unhealthy":
            url = info.get("url", f"http://{name}:8000")
            tasks.append(attempt_heal_agent(name, url, attempts=2, timeout=5.0))
    if not tasks:
        logger.info("✅ All agents healthy - no healing needed")
        return
    try:
        results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=60.0)
        success_count = sum(1 for r in results if hasattr(r, 'status') and r.status in ("recovered", "healthy"))
        failure_count = len(results) - success_count
        logger.info(f"Healing cycle complete: {success_count} succeeded, {failure_count} failed")
    except asyncio.TimeoutError:
        logger.error("⏱️ Auto-heal cycle exceeded 60s timeout")


async def alert_listener():
    if not redis_client:
        logger.error("Redis client not initialized - cannot start alert listener")
        return
    logger.info("Alert listener started - subscribed to 'system_alert' channel")
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("system_alert")
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                logger.info(f"📢 Received alert: {message['data']}")
                try:
                    await auto_heal_all()
                except Exception as e:
                    logger.error(f"Error processing alert: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Alert listener crashed: {e}", exc_info=True)
    finally:
        await pubsub.unsubscribe("system_alert")
        logger.warning("Alert listener stopped")


# ── Routes ──────────────────────────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    docker_ok = False
    if docker_adapter and docker_adapter.client:
        try:
            docker_adapter.client.ping()
            docker_ok = True
        except Exception:
            pass
    redis_ok = redis_client is not None
    bus_ok   = event_bus is not None and event_bus._connected
    status   = "healthy" if (docker_ok and redis_ok) else "degraded"
    return {
        "status": status,
        "healer": "online",
        "redis": redis_ok,
        "docker": docker_ok,
        "event_bus": bus_ok,
        "circuit_breaker_active": len(circuit_breakers) > 0,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/health/sweep")
async def health_sweep():
    if not docker_adapter:
        raise HTTPException(status_code=503, detail="Docker adapter not initialized")
    try:
        return await docker_adapter.check_all_containers()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/xp/status")
async def xp_status():
    if not event_bus:
        raise HTTPException(status_code=503, detail="EventBus not connected")
    return await event_bus.get_agent_xp(HEALER_AGENT_ID)


@app.get("/xp/history")
async def xp_history():
    if not event_bus:
        raise HTTPException(status_code=503, detail="EventBus not connected")
    return await event_bus.get_event_history(agent_type="healer", limit=20)


@app.get("/circuit-breaker/status")
async def circuit_breaker_status():
    return {
        agent: {
            "state": breaker.state.value,
            "failure_count": breaker.failure_count,
            "last_failure_time": breaker.last_failure_time.isoformat() if breaker.last_failure_time else None,
        }
        for agent, breaker in circuit_breakers.items()
    }


@app.get("/circuit-breaker/{agent_name}")
async def circuit_breaker_agent_status(agent_name: str):
    if agent_name not in circuit_breakers:
        raise HTTPException(status_code=404, detail="Agent not found")
    breaker = circuit_breakers[agent_name]
    return {
        "agent": agent_name,
        "state": breaker.state.value,
        "failure_count": breaker.failure_count,
        "threshold": breaker.failure_threshold,
        "timeout_seconds": breaker.recovery_timeout,
        "last_failure_time": breaker.last_failure_time.isoformat() if breaker.last_failure_time else None,
    }


@app.post("/circuit-breaker/reset/{agent_name}")
async def reset_circuit_breaker(agent_name: str):
    if agent_name in circuit_breakers:
        circuit_breakers[agent_name].on_success()
        logger.info(f"Circuit breaker manually reset for {agent_name}")
        return {"message": f"Circuit breaker reset for {agent_name}"}
    return {"message": f"No circuit breaker found for {agent_name}"}


@app.post("/heal")
async def trigger_heal(request: HealRequest) -> HealResult:
    logger.info(f"Manual heal requested for {request.agent_name}")
    return await attempt_heal_agent(request.agent_name, request.agent_url, request.attempts, request.timeout)


@app.post("/alerts/webhook")
async def alert_webhook(request: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(f"🔔 Alert webhook received: {len(request.get('alerts', []))} alerts")
    for alert in request.get("alerts", []):
        status = alert.get("status")
        labels = alert.get("labels", {})
        alert_name = labels.get("alertname")
        instance = labels.get("instance")
        if status == "firing" and alert_name in ["ServiceDown", "ContainerKilled", "ContainerAbsent"]:
            logger.warning(f"🚨 Critical Alert: {alert_name} on {instance}")
            service_name = instance.split(":")[0] if instance else "unknown"
            if service_name != "unknown":
                asyncio.create_task(attempt_heal_agent(agent_name=service_name, agent_url=f"http://{instance}", attempts=2, timeout=10.0))
    return {"status": "processed"}


@app.get("/throttle/state")
async def throttle_state_get():
    return await get_throttle_state()


@app.post("/throttle/state")
async def throttle_state_post(update: ThrottleStateUpdate):
    return await set_throttle_state(update)
