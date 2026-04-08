from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from typing import Dict, Optional
import asyncio
import httpx
import os
import json
import logging
from datetime import datetime, timedelta
import redis.asyncio as redis
from collections import defaultdict
from healer.adapters.docker_adapter import DockerAdapter
from healer.models import HealRequest, HealResult

# Setup logging with JSON format for production
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger("healer.main")
logger.addHandler(handler)
logger.setLevel(logging.INFO)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://crew-orchestrator:8080")

redis_client: Optional[redis.Redis] = None
docker_adapter: Optional[DockerAdapter] = None


# Circuit Breaker Pattern - Prevents infinite retry loops
class CircuitBreaker:
    def __init__(self, failure_threshold=3, timeout=60):
        self.failure_counts = defaultdict(int)
        self.last_failure_time = {}
        self.failure_threshold = failure_threshold
        self.timeout = timeout
    
    def is_open(self, agent_name: str) -> bool:
        """Check if circuit is open (too many failures)"""
        if agent_name not in self.last_failure_time:
            return False
        
        # Reset after timeout
        if datetime.now() - self.last_failure_time[agent_name] > timedelta(seconds=self.timeout):
            self.failure_counts[agent_name] = 0
            return False
        
        return self.failure_counts[agent_name] >= self.failure_threshold
    
    def record_failure(self, agent_name: str):
        self.failure_counts[agent_name] += 1
        self.last_failure_time[agent_name] = datetime.now()
        logger.warning(f"Circuit breaker: {agent_name} failures = {self.failure_counts[agent_name]}/{self.failure_threshold}")
    
    def record_success(self, agent_name: str):
        if self.failure_counts[agent_name] > 0:
            logger.info(f"Circuit breaker: {agent_name} recovered - resetting failure count")
        self.failure_counts[agent_name] = 0
        if agent_name in self.last_failure_time:
            del self.last_failure_time[agent_name]


circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client, docker_adapter
    # Startup
    redis_client = await redis.from_url(REDIS_URL, decode_responses=True)
    docker_adapter = DockerAdapter(redis_url=REDIS_URL)
    
    # Subscribe to orchestrator alerts
    asyncio.create_task(alert_listener())
    
    logger.info("Healer Agent started - monitoring system health")
    
    yield
    
    # Shutdown
    if redis_client:
        await redis_client.close()
    logger.info("Healer Agent shutting down")


app = FastAPI(
    title="Healer Agent", 
    version="0.2.0", 
    description="Autonomous healing service for agents and systems",
    lifespan=lifespan
)


async def fetch_system_health() -> Dict[str, Dict]:
    """Fetch health status of all system components"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{ORCHESTRATOR_URL}/system/health")
            if r.status_code != 200:
                logger.error(f"Failed to fetch system health: {r.status_code}")
                return {}
            return r.json()
    except Exception as e:
        logger.error(f"Error fetching system health: {e}")
        return {}


async def ping_agent_health(agent_url: str, timeout: float) -> bool:
    """Check if an agent responds to health check"""
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
    timeout: float
) -> HealResult:
    """
    Attempt to heal an unhealthy agent with improved timeout handling.
    
    Uses exponential backoff and circuit breaker pattern to prevent
    resource exhaustion from repeatedly healing broken agents.
    """
    
    # Check circuit breaker first
    if circuit_breaker.is_open(agent_name):
        logger.warning(f"Circuit breaker OPEN for {agent_name} - skipping heal attempt")
        return HealResult(
            agent=agent_name,
            status="circuit_open",
            action="none",
            details="Too many consecutive failures - circuit breaker active (will retry in 60s)",
            timestamp=datetime.now().isoformat()
        )
    
    # Phase 1: Check if truly unhealthy
    logger.info(f"Checking health of {agent_name}...")
    healthy = await ping_agent_health(agent_url, timeout)
    if healthy:
        circuit_breaker.record_success(agent_name)
        return HealResult(
            agent=agent_name, 
            status="healthy", 
            action="none", 
            details="No action required", 
            timestamp=datetime.now().isoformat()
        )

    # Phase 2: Restart via Docker Adapter
    logger.warning(f"Agent {agent_name} is unhealthy. Attempting Docker restart...")
    
    if not docker_adapter:
        logger.error("Docker adapter not initialized")
        circuit_breaker.record_failure(agent_name)
        return HealResult(
            agent=agent_name, 
            status="failed", 
            action="restart", 
            details="Docker adapter unavailable", 
            timestamp=datetime.now().isoformat()
        )
    
    restarted = await docker_adapter.restart_container(agent_name)
    if not restarted:
        logger.error(f"Docker restart failed for {agent_name}")
        circuit_breaker.record_failure(agent_name)
        return HealResult(
            agent=agent_name, 
            status="failed", 
            action="restart", 
            details="Docker restart command failed", 
            timestamp=datetime.now().isoformat()
        )
    
    # Phase 3: Wait for recovery with exponential backoff
    wait_times = [2, 5, 10]  # Try after 2s, 5s, 10s
    
    for wait_time in wait_times:
        await asyncio.sleep(wait_time)
        
        try:
            # Add timeout to prevent hanging
            is_healthy = await asyncio.wait_for(
                ping_agent_health(agent_url, timeout), 
                timeout=5.0
            )
            
            if is_healthy:
                logger.info(f"✅ Agent {agent_name} recovered after {wait_time}s")
                circuit_breaker.record_success(agent_name)
                return HealResult(
                    agent=agent_name, 
                    status="recovered", 
                    action="restart", 
                    details=f"Restart successful - recovered after {wait_time}s", 
                    timestamp=datetime.now().isoformat()
                )
        except asyncio.TimeoutError:
            logger.warning(f"Agent {agent_name} still unresponsive after {wait_time}s")
            continue
        except Exception as e:
            logger.error(f"Error checking {agent_name} health: {e}")
            continue
    
    # Failed all attempts
    logger.error(f"❌ Agent {agent_name} failed to recover after restart + 17s wait")
    circuit_breaker.record_failure(agent_name)
    return HealResult(
        agent=agent_name, 
        status="failed", 
        action="restart", 
        details="Agent unresponsive after restart and multiple health checks", 
        timestamp=datetime.now().isoformat()
    )


async def auto_heal_all():
    """
    Heal all unhealthy agents in parallel.
    
    Uses asyncio.gather for concurrent healing to minimize total recovery time.
    Includes global timeout to prevent infinite healing loops.
    """
    logger.info("🔧 Auto-healing triggered by system alert")
    health_data = await fetch_system_health()
    
    if not health_data:
        logger.warning("No health data available - skipping healing cycle")
        return
    
    # Build list of agents that need healing
    tasks = []
    for name, info in health_data.items():
        if info.get("status") == "unhealthy":
            url = info.get("url", f"http://{name}:8000")
            logger.info(f"Queuing healing task for {name}")
            tasks.append(attempt_heal_agent(name, url, attempts=2, timeout=5.0))
    
    if not tasks:
        logger.info("✅ All agents healthy - no healing needed")
        return
    
    # Heal all agents in parallel with global timeout
    try:
        logger.info(f"Healing {len(tasks)} agents in parallel...")
        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=60.0  # Max 60 seconds for entire healing cycle
        )
        
        # Log results
        success_count = 0
        failure_count = 0
        
        for res in results:
            if isinstance(res, Exception):
                logger.error(f"Healing task raised exception: {res}")
                failure_count += 1
            elif res.status == "recovered" or res.status == "healthy":
                logger.info(f"✅ {res.agent}: {res.status} - {res.details}")
                success_count += 1
            else:
                logger.warning(f"❌ {res.agent}: {res.status} - {res.details}")
                failure_count += 1
        
        logger.info(f"Healing cycle complete: {success_count} succeeded, {failure_count} failed")
        
    except asyncio.TimeoutError:
        logger.error("⏱️ Auto-heal cycle exceeded 60s timeout - some agents may still be down")


@app.get("/health")
async def health():
    """Health check endpoint for the Healer Agent itself"""
    docker_ok = False
    if docker_adapter and docker_adapter.client:
        try:
            docker_adapter.client.ping()
            docker_ok = True
        except:
            pass
    
    redis_ok = redis_client is not None
    
    status = "healthy" if (docker_ok and redis_ok) else "degraded"
    
    return {
        "status": status,
        "healer": "online",
        "redis": redis_ok,
        "docker": docker_ok,
        "circuit_breaker_active": len(circuit_breaker.failure_counts) > 0,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health/sweep")
async def health_sweep():
    """
    Checks the health of all containers managed by Docker Adapter.
    Returns detailed report of all container statuses.
    """
    if not docker_adapter:
        raise HTTPException(status_code=503, detail="Docker adapter not initialized")
    
    try:
        report = await docker_adapter.check_all_containers()
        return report
    except Exception as e:
        logger.error(f"Health sweep failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/circuit-breaker/status")
async def circuit_breaker_status():
    """Get current circuit breaker state for all agents"""
    return {
        "failure_counts": dict(circuit_breaker.failure_counts),
        "open_circuits": [
            agent for agent in circuit_breaker.failure_counts.keys()
            if circuit_breaker.is_open(agent)
        ],
        "threshold": circuit_breaker.failure_threshold,
        "timeout_seconds": circuit_breaker.timeout
    }


@app.post("/circuit-breaker/reset/{agent_name}")
async def reset_circuit_breaker(agent_name: str):
    """Manually reset circuit breaker for a specific agent"""
    circuit_breaker.record_success(agent_name)
    logger.info(f"Circuit breaker manually reset for {agent_name}")
    return {"message": f"Circuit breaker reset for {agent_name}"}


@app.post("/heal")
async def trigger_heal(request: HealRequest):
    """Manually trigger healing for a specific agent"""
    logger.info(f"Manual heal requested for {request.agent_name}")
    result = await attempt_heal_agent(
        request.agent_name, 
        request.agent_url, 
        request.attempts, 
        request.timeout
    )
    return result


async def alert_listener():
    """
    Listens for 'system_alert' messages on Redis pubsub and triggers healing.
    Runs continuously in the background as a coroutine.
    """
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


# ============================================
# IMPROVEMENTS IN THIS VERSION:
# ============================================
# 1. ✅ Exponential backoff (2s, 5s, 10s) instead of fixed 5s waits
# 2. ✅ Circuit breaker pattern to prevent infinite retry loops
# 3. ✅ Structured JSON logging for production observability
# 4. ✅ Global timeout (60s) on auto_heal_all to prevent runaway healing
# 5. ✅ Better error handling with specific exception types
# 6. ✅ New endpoints: /circuit-breaker/status and /circuit-breaker/reset
# 7. ✅ Parallel healing with asyncio.gather (already working, kept it)
# 8. ✅ Better logging with success/failure counts
# 9. ✅ Health endpoint shows circuit breaker status
# 10. ✅ Exception handling in alert_listener with try/finally
