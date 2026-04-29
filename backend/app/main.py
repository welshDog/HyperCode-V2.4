import asyncio
import datetime
import json
import logging
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager, suppress

_boot_error: str | None = None

import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
try:
    from opentelemetry import trace as _trace
except Exception:
    _trace = None
try:
    from prometheus_fastapi_instrumentator import Instrumentator as _Instrumentator
except Exception:
    _Instrumentator = None

from app.core.config import settings, get_settings_boot_error

try:
    from app.api.api import api_router
except Exception as exc:
    api_router = None
    _boot_error = _boot_error or f"api_router import failed: {exc}"

_boot_error = _boot_error or get_settings_boot_error()
from app.core.http_security import RateLimitConfig, RateLimitMiddleware, SecurityHeadersMiddleware
from app.db.base_class import Base
from app.db.session import engine
try:
    from app.middleware.rate_limiting import limiter, setup_rate_limiting
except Exception:
    limiter = None
    setup_rate_limiting = None
try:
    from app.routes.stripe import router as stripe_router
except Exception:
    stripe_router = None
try:
    from app.ws.uplink import router as uplink_router
except Exception:
    uplink_router = None

import app.models.broski as _broski
import app.models.dashboard_task as _dashboard_task
import app.models.models as _models
del _broski, _dashboard_task, _models

try:
    from app.core.logging import setup_logging as _setup_logging
    from app.middleware.metrics import MetricsMiddleware as _MetricsMiddleware
    _has_phase5 = True
except Exception:
    _setup_logging = None
    _MetricsMiddleware = None
    _has_phase5 = False

# Shared async Redis client for metrics middleware (initialised at startup)
_metrics_redis: aioredis.Redis | None = None

# DEBUG: Print to stderr to ensure visibility in Docker logs
print("Starting HyperCode Core API...", file=sys.stderr)

# Copyright (C) 2026 HyperCode - All Rights Reserved
# Licensed under the GNU Affero General Public License v3.0 (AGPL-3.0)
# See LICENSE file for details.

# Configure logging — JSON structured if available, plain otherwise
if _has_phase5 and _setup_logging is not None:
    _setup_logging(log_level=os.getenv("LOG_LEVEL", "INFO"))
else:
    logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI Application
@asynccontextmanager
async def _lifespan(app: FastAPI):
    global _metrics_redis
    global _boot_error

    heartbeat_task: asyncio.Task | None = None

    try:
        settings.validate_security()
    except Exception as exc:
        _boot_error = str(exc)
        logger.error("Startup security validation failed: %s", _boot_error)
    else:

        async def _init_db_background() -> None:
            if os.getenv("DB_AUTO_CREATE", "false").strip().lower() == "true":
                try:
                    await asyncio.to_thread(Base.metadata.create_all, bind=engine)
                except Exception:
                    logger.exception("DB_AUTO_CREATE failed (non-fatal)")

            try:
                from app.db.session import SessionLocal
                from app.services.broski_service import seed_achievements

                def _seed_sync() -> None:
                    db = SessionLocal()
                    try:
                        seed_achievements(db)
                    finally:
                        db.close()

                await asyncio.wait_for(asyncio.to_thread(_seed_sync), timeout=8)
            except TimeoutError:
                logger.warning("Seed achievements timed out (non-fatal)")
            except Exception:
                logger.exception("Failed to seed BROski achievements (non-fatal)")

        asyncio.create_task(_init_db_background())

        try:
            redis_client = aioredis.from_url(
                settings.HYPERCODE_REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2,
            )
            await redis_client.ping()
            _metrics_redis = redis_client
            logger.info("Metrics Redis client connected")
            heartbeat_task = asyncio.create_task(_core_heartbeat_loop())
        except Exception:
            logger.warning("Metrics Redis unavailable — metrics middleware will no-op")

        try:
            if setup_rate_limiting is not None:
                setup_rate_limiting(app)
        except Exception:
            logger.exception("Rate limiting init failed (non-fatal)")

        try:
            from app.core.telemetry import setup_telemetry as _setup_telemetry

            _setup_telemetry(app)
        except Exception:
            logger.exception("Telemetry init failed (non-fatal)")

        if os.getenv("PROMETHEUS_METRICS_DISABLED", "false").strip().lower() != "true":
            try:
                if _Instrumentator is not None:
                    _Instrumentator().instrument(app).expose(app)
            except Exception:
                logger.exception("Prometheus instrumentation failed (non-fatal)")

    yield

    logger.info("Shutdown initiated...")
    if heartbeat_task is not None:
        heartbeat_task.cancel()
        with suppress(asyncio.CancelledError):
            await heartbeat_task

    if _metrics_redis is not None:
        await _metrics_redis.aclose()
        _metrics_redis = None

    from app.db.session import engine as _engine

    _engine.dispose()
    logger.info("Graceful shutdown complete")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="HyperCode Core API Service",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=_lifespan,
)

@app.middleware("http")
async def _boot_guard(request: Request, call_next):
    if _boot_error is not None and request.url.path != "/health":
        return JSONResponse(
            status_code=503,
            content={"detail": "Service misconfigured", "boot_error": _boot_error},
        )
    return await call_next(request)

    """
    Publishes hypercode-core heartbeat to Redis every 10s.
    Key: agents:heartbeat:hypercode-core  (TTL 30s)
    Read by GET /api/v1/agents/status to populate the dashboard agent count.
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

if _has_phase5 and _MetricsMiddleware is not None:
    app.add_middleware(_MetricsMiddleware)
    # Gordon Tier 3 — register DB pool collector + Celery queue collector
    # so /metrics emits live SQLAlchemy pool stats and Redis queue depth.
    try:
        from app.middleware.metrics import register_db_pool_collector
        from app.observability.celery_metrics import register_celery_queue_collector

        register_db_pool_collector()
        register_celery_queue_collector()
    except Exception:
        logger.exception("Failed to register Gordon Tier 3 collectors (non-fatal)")
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
        "/api/stripe/webhook",  # 💳 Stripe webhooks must not be rate-limited
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

# Include API Router
if api_router is not None:
    app.include_router(api_router, prefix=settings.API_V1_STR)

# 💳 Phase 10F — Stripe Checkout & Webhook
if stripe_router is not None:
    app.include_router(stripe_router)
if uplink_router is not None:
    app.include_router(uplink_router)  # 🔌 Phase 10J — WS /ws/uplink

@app.get("/health")
async def health_check(request: Request):
    if _boot_error is not None:
        return JSONResponse(
            status_code=200,
            content={
                "status": "degraded",
                "service": settings.SERVICE_NAME,
                "version": settings.VERSION,
                "environment": settings.ENVIRONMENT,
                "boot_error": _boot_error,
            },
        )
    return {
        "status": "ok",
        "service": settings.SERVICE_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }

@app.get("/")
async def root():
    return JSONResponse({"message": "Welcome to HyperCode Core API"})

if _trace is not None:
    tracer = _trace.get_tracer(__name__)

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
# ENDPOINTS (current)
#   GET  /health                      — root liveness check
#   GET  /                            — welcome message
#   GET  /metrics                     — Prometheus scrape endpoint
#   WS   /ws/uplink                   — Mission Control uplink WebSocket
#
#   GET  /api/v1/health               — deep health (Postgres/Redis/Discord + breakers)
#   GET  /api/v1/metrics              — Mission Control metrics snapshot (JSON)
#   GET  /api/v1/agents/status        — agent status list for dashboard
#   GET  /api/v1/system/state         — stable/watch/on_fire snapshot
#   GET  /api/v1/error-budget         — SLO error budget calculation
#   WS   /api/v1/ws/events            — live event stream WebSocket
#   WS   /api/v1/ws/logs              — live log stream WebSocket
#
#   POST /api/v1/auth/*               — auth flows
#   GET  /api/v1/users/*              — user CRUD (JWT required)
#   GET  /api/v1/projects/*           — project CRUD (JWT required)
#   GET  /api/v1/tasks                — task list (JWT required)
#   POST /api/v1/tasks                — create task (JWT required)
#   POST /api/v1/execute              — dashboard command (JWT required)
#   GET  /api/v1/logs                 — dashboard logs (JWT required, from Tasks table)
#   GET  /api/v1/memory/*             — memory endpoints
#   WS   /api/v1/orchestrator/ws/approvals — approvals WebSocket (Redis pub/sub)
#   GET  /api/v1/broski/*             — BROski$ economy endpoints
#   GET  /api/v1/planning/*           — planning endpoints
#   GET  /api/v1/ops/dlq/stats        — DLQ stats (superuser)
#   GET  /api/v1/ops/dlq              — DLQ list (superuser)
#   POST /api/v1/ops/dlq/replay       — DLQ replay (superuser)
#
#   POST /api/stripe/checkout         — Stripe checkout session
#   GET  /api/stripe/plans            — list Stripe plans
#   POST /api/stripe/webhook          — Stripe webhook handler
# =============================================================================
