"""
FastAPI Orchestration Layer for HyperCode Agent Crew
Manages communication between 8 specialized agents
"""

from fastapi import (
    FastAPI,
    HTTPException,
    BackgroundTasks,
    WebSocket,
    WebSocketDisconnect,
    Request,
    Response,
    Depends,
    Security,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import List, Dict, Optional, Any, Union
import httpx
import json
import logging
import asyncio
import os
import hashlib
import secrets
from time import perf_counter
from contextlib import asynccontextmanager
from task_queue import get_redis_pool
import redis.asyncio as redis
from datetime import datetime, timezone
from prometheus_client import Counter
from prometheus_client.exposition import CONTENT_TYPE_LATEST, generate_latest

# Import configuration
from config import settings

# Configure Logging
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("crew-orchestrator")

redis_client: Optional[redis.Redis] = None

# Forward declaration of app
app: FastAPI = None  # type: ignore

# --- LIFECYCLE ---


async def monitor_agent_health():
    """Background task to monitor agent health status"""
    while True:
        try:
            if not redis_client:
                await asyncio.sleep(5)
                continue

            failed_agents = []
            results = {}

            for agent_name in settings.enabled_agent_keys():
                url = settings.agents[agent_name]
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        start_time = datetime.now()
                        response = await client.get(f"{url}/health")
                        latency = (datetime.now() - start_time).total_seconds() * 1000

                        if response.status_code == 200:
                            results[agent_name] = {
                                "status": "healthy",
                                "latency_ms": latency,
                                "last_checked": datetime.now().isoformat(),
                            }
                        else:
                            failed_agents.append(agent_name.replace("_", "-"))
                            results[agent_name] = {
                                "status": "unhealthy",
                                "error": f"Status {response.status_code}",
                                "last_checked": datetime.now().isoformat(),
                            }
                except Exception as e:
                    failed_agents.append(agent_name.replace("_", "-"))
                    results[agent_name] = {
                        "status": "down",
                        "error": str(e),
                        "last_checked": datetime.now().isoformat(),
                    }

            # Store health results in Redis for dashboard
            await redis_client.set("system:health", json.dumps(results))

            # Alert if threshold reached
            if len(failed_agents) >= 4:
                alert_msg = {
                    "type": "CRITICAL_ALERT",
                    "message": f"CRITICAL: {len(failed_agents)} agents are DOWN!",
                    "failed_agents": failed_agents,
                    "timestamp": datetime.now().isoformat(),
                }
                # Publish to dashboard via existing approval channel or new alert channel
                await redis_client.publish("approval_requests", json.dumps(alert_msg))
                logger.critical(
                    f"HEALTH ALERT: {len(failed_agents)} agents down: {failed_agents}"
                )

        except Exception as e:
            logger.error(f"Health monitor error: {e}")

        await asyncio.sleep(30)  # Run every 30 seconds


@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client
    # Startup
    redis_client = await get_redis_pool()
    logger.info("Redis connected")

    # Start background tasks
    monitor_task = asyncio.create_task(monitor_agent_health())
    fan_out_task = asyncio.create_task(_redis_event_fan_out())

    yield

    # Shutdown
    for task in (monitor_task, fan_out_task):
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")


app = FastAPI(
    title="HyperCode Agent Crew Orchestrator",
    description="Coordinates specialized AI agents for software development",
    version="2.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_cors_allow_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: str = Security(api_key_header)) -> str:
    expected = settings.api_key
    if not expected:
        if settings.environment.strip().lower() == "development":
            return api_key or ""
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service misconfigured: ORCHESTRATOR_API_KEY is not set",
        )
    if not api_key or not secrets.compare_digest(api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return api_key


_smoke_request_total = Counter(
    "smoke_request_total", "Total /execute/smoke requests", ["mode", "result"]
)
_smoke_redis_skip_total = Counter(
    "smoke_redis_skip_total", "Redis writes skipped by smoke endpoint"
)

_smoke_key_issued_at: Dict[str, datetime] = {}
_smoke_key_revoked_at: Dict[str, datetime] = {}

_smoke_request_total.labels(mode="noop", result="pass").inc(0)
_smoke_redis_skip_total.inc(0)


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


def _smoke_enabled() -> bool:
    return os.getenv("SMOKE_ENDPOINT_ENABLED", "false").strip().lower() == "true"


def _smoke_key_allowlist() -> set[str]:
    raw = os.getenv("SMOKE_KEY_ALLOWLIST", "").strip()
    if not raw:
        return set()
    return {h.strip() for h in raw.split(",") if h.strip()}


def _smoke_key_ttl_seconds() -> int:
    raw = os.getenv("SMOKE_KEY_TTL_SECONDS", "900").strip()
    try:
        value = int(raw)
        return value if value >= 0 else 900
    except Exception:
        return 900


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _enforce_smoke_guardrails(req: Request) -> None:
    if not _smoke_enabled():
        raise HTTPException(status_code=404, detail="Smoke endpoint disabled")

    if req.headers.get("x-smoke-mode") != "true":
        raise HTTPException(status_code=403, detail="Missing X-Smoke-Mode: true")

    raw_key = req.headers.get("x-api-key")
    if not raw_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key")

    allowlist = _smoke_key_allowlist()
    if not allowlist:
        raise HTTPException(status_code=503, detail="Smoke allowlist not configured")

    key_hash = _hash_key(raw_key)
    if key_hash not in allowlist:
        raise HTTPException(status_code=403, detail="Benchmark key not allowed")

    now = datetime.now(timezone.utc)
    for k, revoked_at in list(_smoke_key_revoked_at.items()):
        if (now - revoked_at).total_seconds() > 86400:
            _smoke_key_revoked_at.pop(k, None)

    if key_hash in _smoke_key_revoked_at:
        raise HTTPException(status_code=403, detail="Benchmark key revoked")

    issued_at = _smoke_key_issued_at.get(key_hash)
    ttl = _smoke_key_ttl_seconds()
    if not issued_at:
        _smoke_key_issued_at[key_hash] = now
        return

    if (now - issued_at).total_seconds() > ttl:
        _smoke_key_issued_at.pop(key_hash, None)
        _smoke_key_revoked_at[key_hash] = now
        raise HTTPException(status_code=403, detail="Benchmark key TTL expired")


# --- EXECUTION ENDPOINTS ---


class TaskDefinition(BaseModel):
    id: str
    type: str
    description: str
    agent: Optional[str] = None
    agents: Optional[List[str]] = None
    requires_approval: bool = True
    workflow: Optional[str] = None


class ExecuteRequest(BaseModel):
    task: Optional[Union[TaskDefinition, str]] = None
    id: Optional[str] = None
    type: Optional[str] = None
    description: Optional[str] = None
    agent: Optional[str] = None
    agents: Optional[List[str]] = None
    agent_type: Optional[str] = None
    task_id: Optional[str] = None
    requires_approval: Optional[bool] = None


class AgentTaskRequest(BaseModel):
    id: Optional[str] = None
    task: Optional[str] = None
    description: Optional[str] = None
    type: str = "generic"
    context: Optional[Dict[str, Any]] = None
    agent: Optional[str] = None
    requires_approval: bool = False

    # Accept arbitrary extra fields to prevent 422 if caller sends extra keys
    model_config = {
        "extra": "allow"
    }


class SmokeRequest(BaseModel):
    mode: str = "noop"
    agent: Optional[str] = None


class SmokeAgentResult(BaseModel):
    status: str
    http_status: Optional[int] = None
    latency_ms: Optional[float] = None
    error: Optional[str] = None


class SmokeResponse(BaseModel):
    smoke: str
    mode: str
    latency_ms: float
    redis_writes_skipped: int
    approval_skipped: bool
    agent: Optional[str] = None
    agent_http_status: Optional[int] = None
    agent_latency_ms: Optional[float] = None
    healthy: Optional[int] = None
    total: Optional[int] = None
    agents: Optional[Dict[str, SmokeAgentResult]] = None
    timestamp: str


# Helper to log to Redis
async def log_event(agent: str, level: str, msg: str):
    if redis_client:
        entry = {
            "id": datetime.now().timestamp(),
            "time": datetime.now().strftime("%H:%M:%S"),
            "agent": agent,
            "level": level,
            "msg": msg,
        }
        await redis_client.lpush("logs:global", json.dumps(entry))
        await redis_client.ltrim("logs:global", 0, 99)  # Keep last 100


async def request_approval(
    task_id: str, description: str, agent: Optional[str] = None
) -> str:
    """Helper to handle approval workflow"""
    if not redis_client:
        logger.error("Redis not connected, cannot request approval")
        return "error"

    approval_id = f"approval-{task_id}"
    if agent:
        approval_id += f"-{agent}"

    approval_request = {
        "id": approval_id,
        "task_id": task_id,
        "description": description,
        "agent": agent,
        "plan": (
            "Generated plan based on RAG..."
            if not agent
            else f"Execute specific tasks for {agent}"
        ),
        "risk_level": "Low",
        "estimated_time": "2 minutes",
    }

    # Publish to Redis for Dashboard
    await redis_client.publish("approval_requests", json.dumps(approval_request))
    log_msg = f"Approval requested for task {task_id}"
    if agent:
        log_msg += f" ({agent})"
    await log_event("orchestrator", "warn", log_msg)

    status = "pending"
    timeout = 60
    start_time = datetime.now()

    while status == "pending":
        if (datetime.now() - start_time).seconds > timeout:
            await log_event("orchestrator", "error", f"Approval timeout for {task_id}")
            return "timeout"

        response = await redis_client.get(f"approval:{approval_id}:response")
        if response:
            data = json.loads(response)
            status = data.get("status")
        else:
            await asyncio.sleep(1)

    await log_event("orchestrator", "success", f"Approval received: {status}")
    return status


def _route_agent_for_task_type(task_type: str) -> Optional[str]:
    normalized = (task_type or "").strip().lower()
    if normalized == "code_generation":
        return "coder"
    if normalized in ("spawn_agent", "evolve"):
        return "agent-x"
    return None


@app.post("/execute")
async def execute_task(
    request: ExecuteRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(require_api_key),
):
    task: TaskDefinition
    if isinstance(request.task, TaskDefinition):
        task = request.task
    else:
        legacy_description = request.description
        if not legacy_description and isinstance(request.task, str):
            legacy_description = request.task

        legacy_agent = request.agent or request.agent_type
        legacy_agents = request.agents

        task_id = (
            request.id
            or request.task_id
            or f"legacy-{int(datetime.now().timestamp() * 1000)}"
        )
        task_type = request.type or "legacy"
        requires_approval = (
            request.requires_approval
            if request.requires_approval is not None
            else False
        )

        if not legacy_description:
            raise HTTPException(status_code=422, detail="Missing task description")

        task = TaskDefinition(
            id=task_id,
            type=task_type,
            description=legacy_description,
            agent=legacy_agent,
            agents=legacy_agents,
            requires_approval=requires_approval,
        )

    # 1. Log Receipt
    logger.info(
        json.dumps(
            {
                "event": "task_received",
                "task_id": task.id,
                "agent": task.agent or task.agents,
            }
        )
    )

    # Store Task in Redis
    if redis_client:
        task_data = task.dict()
        task_data["status"] = "in_progress"
        task_data["started_at"] = datetime.now().isoformat()
        task_data["progress"] = 0
        task_data["steps"] = task.agents or [task.agent]
        await redis_client.set(f"task:{task.id}:details", json.dumps(task_data))
        await redis_client.lpush("tasks:history", task.id)
        await redis_client.ltrim("tasks:history", 0, 99)

        await log_event("orchestrator", "info", f"Received task: {task.id}")

    # 2. RAG Query — retrieve relevant context from shared agent memory
    rag_context: str = ""
    try:
        import sys
        import os
        _shared_path = os.path.join(os.path.dirname(__file__), "..", "shared")
        if _shared_path not in sys.path:
            sys.path.insert(0, _shared_path)
        from rag_memory import AgentMemory  # type: ignore[import]
        _agent_memory = AgentMemory(agent_name="crew-orchestrator")
        rag_context = _agent_memory.query_relevant_context(task.description, top_k=3)
        logger.info(
            json.dumps(
                {
                    "event": "rag_query",
                    "query": task.description[:50],
                    "chunks_retrieved": len(rag_context.split("---")) if rag_context else 0,
                }
            )
        )
    except Exception as rag_exc:
        # ChromaDB may not be available in all environments; degrade gracefully
        logger.warning(
            json.dumps({"event": "rag_query_failed", "reason": str(rag_exc)})
        )

    # 3. Plan Generation — build execution plan enriched by RAG context
    plan_description = task.description
    if rag_context:
        plan_description = f"{task.description}\n\n[Context]\n{rag_context[:500]}"
    logger.info(
        json.dumps(
            {
                "event": "plan_generated",
                "task_id": task.id,
                "has_rag_context": bool(rag_context),
            }
        )
    )

    # 4. Approval Flow
    if task.requires_approval:
        status = await request_approval(task.id, task.description, task.agent)
        if status != "approved":
            return {"status": "rejected" if status != "timeout" else "timeout"}

    # 5. Execute Agent(s)
    agents_to_run = []
    if task.agents:
        agents_to_run = task.agents
    elif task.agent:
        agents_to_run = [task.agent]

    results = {}

    # Update progress
    if redis_client:
        task_data = json.loads(await redis_client.get(f"task:{task.id}:details"))
        task_data["progress"] = 10
        await redis_client.set(f"task:{task.id}:details", json.dumps(task_data))

    for i, agent_name in enumerate(agents_to_run):
        await log_event(
            agent_name, "info", f"Starting execution phase {i+1}/{len(agents_to_run)}"
        )

        # Mark agent as busy
        if redis_client:
            await redis_client.set(f"agent:{agent_name}:current_task", task.id)

            # Update progress
            task_data = json.loads(await redis_client.get(f"task:{task.id}:details"))
            task_data["progress"] = 10 + int((i / len(agents_to_run)) * 80)
            await redis_client.set(f"task:{task.id}:details", json.dumps(task_data))

        # Approval for multi-agent (Test 2/3)
        if len(agents_to_run) > 1 and task.requires_approval:
            desc = f"Execute phase for {agent_name}: {task.description[:50]}..."
            status = await request_approval(task.id, desc, agent_name)

            if status != "approved":
                return {
                    "status": "rejected" if status != "timeout" else "timeout",
                    "agent": agent_name,
                }

        # Determine agent URL — only allowlisted agents are permitted
        agent_key = agent_name.replace("-", "_")
        agent_url = settings.agents.get(agent_key)

        if not agent_url:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown agent: '{agent_name}'. Must be one of: {list(settings.agents.keys())}",
            )

        # Call the agent
        try:
            async with httpx.AsyncClient() as client:
                agent_payload = {
                    "id": task.id,
                    "task": plan_description,
                    "type": task.type,
                    "requires_approval": False,
                }

                response = await client.post(
                    f"{agent_url}/execute", json=agent_payload, timeout=120.0
                )
                if response.status_code == 200:
                    result = response.json()
                    await log_event(
                        agent_name, "success", "Task completed successfully"
                    )
                    results[agent_name] = result
                else:
                    await log_event(
                        agent_name, "error", f"Failed: status={response.status_code}"
                    )
                    results[agent_name] = {
                        "status": "error",
                        "message": "Agent execution failed",
                    }
                    return {"status": "error", "message": "Agent execution failed"}

        except Exception:
            await log_event(agent_name, "error", "Exception during agent execution")
            logger.exception("Agent execution exception")
            return {"status": "error", "message": "Agent execution failed"}
        finally:
            # Mark agent as idle
            if redis_client:
                await redis_client.delete(f"agent:{agent_name}:current_task")

    # Final update
    if redis_client:
        task_data = json.loads(await redis_client.get(f"task:{task.id}:details"))
        task_data["progress"] = 100
        task_data["status"] = "completed"
        await redis_client.set(f"task:{task.id}:details", json.dumps(task_data))
        await log_event("orchestrator", "success", "Workflow completed")

        # Publish BROski$ reward event — backend Celery / Discord bot listens
        broski_event = {
            "event": "task_completed",
            "task_id": task.id,
            "task_type": task.type,
            "agents": list(results.keys()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await redis_client.publish("broski_events", json.dumps(broski_event))
        logger.info(
            json.dumps({"event": "broski_event_published", "task_id": task.id})
        )

    return {"status": "completed", "message": "Workflow finished", "results": results}


@app.post("/task")
async def dispatch_task(
    request: AgentTaskRequest,
    api_key: str = Depends(require_api_key),
):
    task_text = request.task or request.description
    if not task_text and request.context and isinstance(request.context, dict):
        context_description = request.context.get("description")
        if isinstance(context_description, str) and context_description.strip():
            task_text = context_description.strip()
    if not task_text:
        raise HTTPException(status_code=422, detail="Missing task")

    task_id = request.id or f"task-{int(datetime.now().timestamp() * 1000)}"
    task_type = request.type or "generic"

    agent_name = request.agent or _route_agent_for_task_type(task_type)
    if not agent_name:
        raise HTTPException(status_code=422, detail="Unable to route task type")

    agent_key = agent_name.replace("-", "_")
    agent_url = settings.agents.get(agent_key)
    if not agent_url:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown agent: '{agent_name}'. Must be one of: {list(settings.agents.keys())}",
        )

    payload = {
        "id": task_id,
        "task": task_text,
        "type": task_type,
        "context": request.context or {},
        "requires_approval": False,
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{agent_url}/execute", json=payload, timeout=120.0)
        if resp.status_code != 200:
            logger.error(
                json.dumps(
                    {
                        "event": "task_dispatch_failed",
                        "task_id": task_id,
                        "agent": agent_name,
                        "http_status": resp.status_code,
                    }
                )
            )
            raise HTTPException(status_code=502, detail="Agent execution failed")
        return {
            "status": "completed",
            "task_id": task_id,
            "agent": agent_name,
            "result": resp.json(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Task dispatch exception")
        raise HTTPException(status_code=502, detail=str(exc))


@app.post("/execute/smoke", response_model=SmokeResponse)
async def execute_smoke(
    request: SmokeRequest,
    req: Request,
):
    _enforce_smoke_guardrails(req)

    mode = (request.mode or "noop").strip().lower()
    t0 = perf_counter()

    if mode == "noop":
        _smoke_request_total.labels(mode="noop", result="pass").inc()
        _smoke_redis_skip_total.inc(1)
        latency_ms = (perf_counter() - t0) * 1000.0
        return SmokeResponse(
            smoke="pass",
            mode="noop",
            latency_ms=round(latency_ms, 2),
            redis_writes_skipped=1,
            approval_skipped=True,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    if mode != "probe_health":
        _smoke_request_total.labels(mode=mode, result="fail").inc()
        raise HTTPException(status_code=422, detail="Invalid mode")

    targets: Dict[str, str] = {}
    if request.agent:
        key = request.agent.replace("-", "_")
        url = settings.agents.get(key)
        if not url:
            _smoke_request_total.labels(mode="probe_health", result="fail").inc()
            raise HTTPException(status_code=404, detail="Agent not in roster")
        targets[key] = url
    else:
        targets = dict(settings.agents)

    async def probe(name: str, url: str) -> tuple[str, SmokeAgentResult]:
        try:
            start = perf_counter()
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{url}/health")
            agent_latency_ms = (perf_counter() - start) * 1000.0
            if resp.status_code == 200:
                return name, SmokeAgentResult(
                    status="healthy",
                    http_status=resp.status_code,
                    latency_ms=round(agent_latency_ms, 2),
                )
            return name, SmokeAgentResult(
                status="unhealthy",
                http_status=resp.status_code,
                latency_ms=round(agent_latency_ms, 2),
            )
        except Exception as e:
            return name, SmokeAgentResult(status="down", error=type(e).__name__)

    results = await asyncio.gather(*[probe(n, u) for n, u in targets.items()])
    agents = {name: result for name, result in results}
    healthy = sum(1 for r in agents.values() if r.status == "healthy")
    total = len(agents)

    smoke = "pass" if healthy == total else "partial" if healthy > 0 else "fail"
    _smoke_request_total.labels(mode="probe_health", result=smoke).inc()
    _smoke_redis_skip_total.inc(total + 1)

    latency_ms = (perf_counter() - t0) * 1000.0
    return SmokeResponse(
        smoke=smoke,
        mode="probe_health",
        latency_ms=round(latency_ms, 2),
        redis_writes_skipped=total + 1,
        approval_skipped=True,
        agent=request.agent,
        healthy=healthy,
        total=total,
        agents=agents,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# --- WEBSOCKET FOR APPROVALS ---
connected_dashboards: List[WebSocket] = []
_dashboards_lock = asyncio.Lock()

# --- WEBSOCKETS ---


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> bool:
        expected = settings.api_key
        if expected:
            provided = websocket.headers.get("x-api-key") or websocket.query_params.get(
                "api_key"
            )
            if provided != expected:
                await websocket.accept()
                await websocket.close(code=1008)
                return False
        await websocket.accept()
        self.active_connections.append(websocket)
        return True

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting: {e}")


manager = ConnectionManager()


@app.websocket("/ws/uplink")
async def websocket_endpoint(websocket: WebSocket):
    """Real-time task dispatch over WebSocket.

    Message types accepted:
      - ``execute``  — dispatch a task; responds with ``ack`` then publishes
                       progress updates via the ``ws_tasks`` Redis channel.
      - ``ping``     — liveness check; responds with ``pong``.
    """
    if not await manager.connect(websocket):
        return
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_text(
                    json.dumps({"type": "error", "payload": "Invalid JSON"})
                )
                continue

            msg_type = message.get("type")

            if msg_type == "ping":
                await websocket.send_text(
                    json.dumps({"type": "pong", "source": "orchestrator"})
                )

            elif msg_type == "execute":
                payload = message.get("payload") or {}
                task_id = payload.get("id") or f"ws-{int(datetime.now().timestamp() * 1000)}"
                # Acknowledge immediately so the client knows it was received
                await websocket.send_text(
                    json.dumps(
                        {
                            "id": message.get("id"),
                            "type": "ack",
                            "source": "orchestrator",
                            "payload": {"task_id": task_id, "status": "queued"},
                        }
                    )
                )
                # Publish into Redis task channel so the background worker picks it up
                if redis_client:
                    task_payload = {
                        "id": task_id,
                        "type": payload.get("type", "ws_command"),
                        "description": payload.get("description", ""),
                        "agent": payload.get("agent"),
                        "agents": payload.get("agents"),
                        "requires_approval": payload.get("requires_approval", False),
                        "source": "websocket",
                    }
                    await redis_client.publish("ws_tasks", json.dumps(task_payload))
                    logger.info(
                        json.dumps({"event": "ws_task_queued", "task_id": task_id})
                    )

            else:
                await websocket.send_text(
                    json.dumps(
                        {
                            "id": message.get("id"),
                            "type": "error",
                            "source": "orchestrator",
                            "payload": f"Unknown message type: {msg_type!r}",
                        }
                    )
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Client disconnected from uplink")


@app.websocket("/ws/approvals")
async def websocket_approvals(websocket: WebSocket):
    expected = settings.api_key
    if expected:
        provided = websocket.headers.get("x-api-key") or websocket.query_params.get(
            "api_key"
        )
        if provided != expected:
            await websocket.accept()
            await websocket.close(code=1008)
            return
    await websocket.accept()
    async with _dashboards_lock:
        connected_dashboards.append(websocket)
    logger.info("Dashboard connected to approval stream")

    try:
        # Create a new Redis connection for subscribing
        pubsub_redis = await redis.from_url(settings.redis_url, decode_responses=True)
        pubsub = pubsub_redis.pubsub()
        await pubsub.subscribe("approval_requests")

        async for message in pubsub.listen():
            if message["type"] == "message":
                # Forward approval request to dashboard
                await websocket.send_text(message["data"])

    except WebSocketDisconnect:
        logger.info("Dashboard disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        async with _dashboards_lock:
            try:
                connected_dashboards.remove(websocket)
            except ValueError:
                pass


@app.post("/approvals/respond")
async def respond_to_approval(
    response: Dict[str, Any],
    api_key: str = Depends(require_api_key),
):
    """Endpoint for Dashboard to approve/reject tasks"""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not connected")

    approval_id = response.get("approval_id")
    if not approval_id:
        raise HTTPException(status_code=400, detail="Missing approval_id")

    # Store the response where the waiting agent can find it
    await redis_client.set(
        f"approval:{approval_id}:response",
        json.dumps(response),
        ex=3600,  # Expire in 1 hour
    )

    return {"status": "response_recorded"}


@app.get("/system/health")
async def get_system_health(api_key: str = Depends(require_api_key)):
    """Return cached health data for all agents"""
    if not redis_client:
        raise HTTPException(status_code=503, detail="Redis not connected")

    health_data = await redis_client.get("system:health")
    if not health_data:
        return {"status": "initializing", "agents": {}}

    return json.loads(health_data)


@app.get("/")
async def root():
    return {
        "service": "HyperCode Agent Crew Orchestrator",
        "version": "2.0",
        "agents": settings.enabled_agent_keys(),
        "status": "operational",
    }


@app.get("/health")
async def health_check():
    """Simple health check endpoint for Docker"""
    return {"status": "ok", "service": "crew-orchestrator"}


# --- DASHBOARD ENDPOINTS ---


@app.get("/agents")
async def get_agents(api_key: str = Depends(require_api_key)):
    """Get status of all agents"""
    # In a real system, we'd query Prometheus or Docker
    # For now, we return the configured agents with 'idle' status
    # unless we track them in Redis

    agents_list = []
    for key in settings.enabled_agent_keys():
        url = settings.agents[key]
        # Clean up name
        name = key.replace("_", " ").title()
        role = key.split("_")[-1].title() if "_" in key else "Agent"

        # Check Redis for status if available
        status = "idle"
        cpu = 0
        ram = 0

        if redis_client:
            # Check if agent is busy
            # This key would be set during execution
            current_task = await redis_client.get(f"agent:{key}:current_task")
            if current_task:
                status = "working"
                cpu = 45 + (len(name) * 2)  # Mock variation
                ram = 30 + (len(name) * 3)
            else:
                # Mock idle stats
                cpu = 1 + (len(name) % 5)
                ram = 10 + (len(name) % 10)

        agents_list.append(
            {
                "id": key,
                "name": name,
                "role": role,
                "status": status,
                "cpu": cpu,
                "ram": ram,
                "url": url,
            }
        )

    return agents_list


@app.get("/tasks")
async def get_tasks(api_key: str = Depends(require_api_key)):
    """Get recent tasks"""
    if not redis_client:
        return []

    # Get last 10 tasks from a list
    task_ids = await redis_client.lrange("tasks:history", 0, 9)
    tasks = []

    for tid in task_ids:
        task_data = await redis_client.get(f"task:{tid}:details")
        if task_data:
            tasks.append(json.loads(task_data))

    return tasks


@app.get("/logs")
async def get_logs(api_key: str = Depends(require_api_key)):
    """Get recent system logs"""
    if not redis_client:
        return []

    # Get last 50 logs
    logs = await redis_client.lrange("logs:global", 0, 49)
    return [json.loads(log) for log in logs]


# ── WebSocket event stream ────────────────────────────────────────────────────
# Subscribes to Redis pub/sub channels and broadcasts all agent activity to
# connected dashboard clients in real time.

_ws_clients: set[WebSocket] = set()


async def _broadcast(message: str) -> None:
    """Send a message to all connected WebSocket clients, dropping dead ones."""
    dead: set[WebSocket] = set()
    for ws in _ws_clients:
        try:
            await ws.send_text(message)
        except Exception:
            dead.add(ws)
    _ws_clients.difference_update(dead)


async def _redis_event_fan_out() -> None:
    """Background task: subscribe to Redis channels and fan out to WS clients."""
    if not redis_client:
        return
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("ws_tasks", "broski_events", "approval_requests")
    try:
        async for raw in pubsub.listen():
            if raw["type"] != "message":
                continue
            channel = raw["channel"]
            if isinstance(channel, bytes):
                channel = channel.decode()
            try:
                data = json.loads(raw["data"])
            except Exception:
                continue
            envelope = json.dumps({"channel": channel, "data": data})
            await _broadcast(envelope)
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe()
        await pubsub.aclose()


@app.websocket("/ws/events")
async def ws_events(websocket: WebSocket):
    """
    Real-time event stream for Mission Control Dashboard.
    Pushes agent tasks, BROski rewards, and approval requests as they happen.

    Message format: { "channel": "ws_tasks"|"broski_events"|..., "data": {...} }
    """
    await websocket.accept()
    _ws_clients.add(websocket)

    # Send the last 20 log entries as initial state
    if redis_client:
        try:
            recent = await redis_client.lrange("logs:global", 0, 19)
            for raw in reversed(recent):
                try:
                    entry = json.loads(raw)
                    await websocket.send_text(
                        json.dumps({"channel": "logs:history", "data": entry})
                    )
                except Exception:
                    pass
        except Exception:
            pass

    try:
        # Keep the connection open; client pings keep it alive
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        _ws_clients.discard(websocket)


