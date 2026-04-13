from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from prometheus_fastapi_instrumentator import Instrumentator
from opentelemetry import trace
from app.core.config import settings
from app.core.telemetry import setup_telemetry
from app.api.api import api_router
from app.core.http_security import SecurityHeadersMiddleware, RateLimitMiddleware, RateLimitConfig

try:
    from app.core.logging import setup_logging as _setup_logging
    from app.middleware.metrics import MetricsMiddleware as _MetricsMiddleware
    _HAS_PHASE5 = True
except Exception:
    _HAS_PHASE5 = False
from app.db.base_class import Base
from app.db.session import engine
import app.models.models as _models
del _models
import app.models.broski as _broski
del _broski
import app.models.dashboard_task as _dashboard_task
del _dashboard_task
import asyncio
import datetime
import json
import logging
import os
import sys
import time
import uuid
import redis.asyncio as aioredis

# Shared async Redis client for metrics middleware (initialised at startup)
_metrics_redis: aioredis.Redis | None = None

# DEBUG: Print to stderr to ensure visibility in Docker logs
print("Starting HyperCode Core API...", file=sys.stderr)

# Copyright (C) 2026 HyperCode - All Rights Reserved
# Licensed under the GNU Affero General Public License v3.0 (AGPL-3.0)
# See LICENSE file for details.

# Configure logging — JSON structured if available, plain otherwise
if _HAS_PHASE5:
    _setup_logging(log_level=os.getenv("LOG_LEVEL", "INFO"))
else:
    logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI Application
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="HyperCode Core API Service",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

@app.on_event("shutdown")
async def _shutdown_event() -> None:
    global _metrics_redis
    logger.info("Shutdown initiated...")
    if _metrics_redis is not None:
        await _metrics_redis.aclose()
    from app.db.session import engine as _engine
    _engine.dispose()
    logger.info("Graceful shutdown complete")


@app.on_event("startup")
async def _startup_validate_security() -> None:
    global _metrics_redis
    settings.validate_security()
    if os.getenv("DB_AUTO_CREATE", "false").strip().lower() == "true":
        Base.metadata.create_all(bind=engine)
    try:
        from app.db.session import SessionLocal
        from app.services.broski_service import seed_achievements
        db = SessionLocal()
        try:
            seed_achievements(db)
        finally:
            db.close()
    except Exception:
        logger.exception("Failed to seed BROski achievements")
    try:
        _metrics_redis = aioredis.from_url(
            settings.HYPERCODE_REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
        )
        await _metrics_redis.ping()
        logger.info("Metrics Redis client connected")
        # Start background heartbeat so dashboard shows this service as an active agent
        asyncio.create_task(_core_heartbeat_loop())
    except Exception:
        logger.warning("Metrics Redis unavailable — metrics middleware will no-op")

async def _core_heartbeat_loop() -> None:
    """
    Publishes hypercode-core heartbeat to Redis every 10s.
    Key: agents:heartbeat:hypercode-core  (TTL 30s)
    Read by GET /api/v1/agents/status to populate the dashboard agent count.
    """
    key = "agents:heartbeat:hypercode-core"
    while True:
        if _metrics_redis is not None:
            try:
                await _metrics_redis.hset(
                    key,
                    mapping={
                        "name": "hypercode-core",
                        "status": "online",
                        "last_seen": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    },
                )
                await _metrics_redis.expire(key, 30)
            except Exception:
                pass
        await asyncio.sleep(10)


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parsed_cors_allow_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

if _HAS_PHASE5:
    app.add_middleware(_MetricsMiddleware)
app.add_middleware(SecurityHeadersMiddleware, enable_hsts=True)
app.add_middleware(
    RateLimitMiddleware,
    config=RateLimitConfig(
        enabled=settings.RATE_LIMIT_ENABLED,
        window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
        max_requests=settings.RATE_LIMIT_MAX_REQUESTS,
    ),
    exempt_paths=(
        "/health",
        f"{settings.API_V1_STR}/docs",
        f"{settings.API_V1_STR}/redoc",
        f"{settings.API_V1_STR}/openapi.json",
        "/openapi.json",
        "/metrics",
    ),
)

@app.middleware("http")
async def _http_metrics_middleware(request: Request, call_next):
    """
    Task 10 — HTTP metrics middleware.
    Writes per-minute request counts, response times, and error counts to Redis.
    Keys consumed by GET /api/v1/metrics to build MetricsSnapshot.
    """
    t0 = time.monotonic()
    response = await call_next(request)
    elapsed_ms = round((time.monotonic() - t0) * 1000, 2)

    if _metrics_redis is not None:
        try:
            minute_key = datetime.datetime.utcnow().strftime("%Y%m%d%H%M")
            async with _metrics_redis.pipeline(transaction=False) as pipe:
                pipe.incr(f"req_count:{minute_key}")
                pipe.expire(f"req_count:{minute_key}", 120)
                pipe.lpush("response_times", elapsed_ms)
                pipe.ltrim("response_times", 0, 99)
                if response.status_code >= 400:
                    pipe.incr(f"error_count:{minute_key}")
                    pipe.expire(f"error_count:{minute_key}", 120)
                # Publish to hypercode:logs — skip noisy health/metrics pings
                _SKIP_LOG_PATHS = {"/health", "/metrics", "/"}
                if request.url.path not in _SKIP_LOG_PATHS:
                    _level = "error" if response.status_code >= 500 else "warn" if response.status_code >= 400 else "info"
                    _entry = json.dumps({
                        "id": str(uuid.uuid4())[:8],
                        "time": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "agent": "hypercode-core",
                        "level": _level,
                        "msg": f"{request.method} {request.url.path} \u2192 {response.status_code} ({elapsed_ms}ms)",
                    })
                    pipe.rpush("hypercode:logs", _entry)
                    pipe.ltrim("hypercode:logs", -1000, -1)
                await pipe.execute()
        except Exception:
            pass  # Never let metrics writing break a real request

    return response


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception")
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

# Initialize OpenTelemetry
setup_telemetry(app)

# Prometheus Instrumentation
if os.getenv("PROMETHEUS_METRICS_DISABLED", "false").strip().lower() != "true":
    instrumentator = Instrumentator().instrument(app).expose(app)

# Include API Router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health")
async def health_check():
    return JSONResponse({
        "status": "ok",
        "service": settings.SERVICE_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    })

@app.get("/")
async def root():
    return JSONResponse({"message": "Welcome to HyperCode Core API"})

# Example Endpoint for Custom Tracing
tracer = trace.get_tracer(__name__)

@app.get("/api/v1/trace-example")
async def trace_example():
    with tracer.start_as_current_span("custom_operation") as span:
        span.set_attribute("custom.attribute", "example_value")
        logger.info("Performing a traced operation")
        await asyncio.sleep(0.1)  # Simulate work
        with tracer.start_as_current_span("inner_operation"):
            logger.info("Inside inner operation")
            await asyncio.sleep(0.05)
    return {"message": "Traced operation completed"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)

# =============================================================================
# DASHBOARD ENDPOINT AUDIT — 2026-04-01
# =============================================================================
#
# EXISTING ENDPOINTS (all under /api/v1 prefix):
#   GET  /health                          — liveness check (root level)
#   GET  /                                — welcome message (root level)
#   GET  /metrics                         — Prometheus scrape endpoint
#   GET  /api/v1/trace-example            — OTel demo
#   POST /api/v1/auth/*                   — auth flows
#   GET  /api/v1/users/*                  — user CRUD (JWT required)
#   GET  /api/v1/projects/*               — project CRUD (JWT required)
#   GET  /api/v1/tasks/                   — task list (JWT required)
#   POST /api/v1/tasks/                   — create task (JWT required)
#   POST /api/v1/execute                  — dashboard command (JWT required)
#   GET  /api/v1/logs                     — dashboard logs (JWT required, from Tasks table)
#   GET  /api/v1/memory/*                 — memory endpoints
#   WS   /api/v1/orchestrator/ws/approvals — approvals WebSocket (Redis pub/sub)
#   GET  /api/v1/broski/*                 — BROski$ economy endpoints
#   GET  /api/v1/planning/*               — planning endpoints
#
# MISSING ENDPOINTS (needed by dashboard — causes "—" display values):
#   GET  /api/v1/metrics                  — MetricsSnapshot JSON (useMetrics.ts polls this)
#   GET  /api/v1/agents/status            — agent online/offline status (useAgentStatus.ts)
#   GET  /api/v1/events                   — SSE event stream (useEventStream.ts)
#   GET  /api/v1/logs (public/no auth)    — log list without JWT (useLogs.ts)
#   GET  /api/v1/system/state             — stable/watch/on_fire state
#   GET  /api/v1/error-budget             — SLO error budget calculation
#   WS   /ws/metrics                      — 5s broadcast MetricsSnapshot
#   WS   /ws/agents                       — agent heartbeat broadcast
#   WS   /ws/events                       — live event stream WebSocket
#   WS   /ws/logs                         — live log stream WebSocket
#
# BROKEN FRONTEND HOOKS:
#   useAgentStatus.ts   → WS  ws://localhost:8081/ws/agents   (8081 = crew-orchestrator, no such endpoint)
#   useEventStream.ts   → WS  ws://${host}:8081/ws/events     (same wrong port/endpoint)
#   useLogs.ts          → WS  ws://${host}:8081/ws/events     (same wrong port/endpoint)
#
# FIX PLAN (tasks 2–12):
#   Task 2  — GET /api/v1/metrics + WS /ws/metrics (metrics_broadcaster.py)
#   Task 3  — GET /api/v1/agents/status + WS /ws/agents (agent heartbeat)
#   Task 4  — Fix frontend hooks to point at port 8000
#   Task 5  — GET /api/v1/events SSE + WS /ws/events (events_broadcaster.py)
#   Task 6  — GET /api/v1/logs (no auth) + WS /ws/logs (logs_broadcaster.py)
#   Task 7  — GET /api/v1/error-budget (reliability.py)
#   Task 8  — GET /api/v1/system/state (extended health)
#   Task 9  — Public task CRUD at /api/tasks + Alembic migration
#   Task 10 — HTTP metrics middleware (req count, response times, error rate in Redis)
#   Task 11 — Frontend Zustand focus-mode store + FocusToggle component
#   Task 12 — Backend tests for all new endpoints/WS/middleware
# =============================================================================
