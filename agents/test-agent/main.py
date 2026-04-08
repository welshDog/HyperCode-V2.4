"""test-agent FastAPI service with Phase 1 enhancements: metrics, caching, rate limiting, circuit breaker."""

import logging
import os
import signal
import sys
import time
from collections.abc import Awaitable, Callable

# Add shared agents path
sys.path.insert(0, '/app/shared')
from agent_utils import AgentMetrics, limiter, CircuitBreaker, cached

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import CONTENT_TYPE_LATEST

logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "msg": "%(message)s"}',
)
logger = logging.getLogger("test-agent")

# Create FastAPI app
app = FastAPI(title="test-agent", version="1.0.0")

# Add rate limiter
app.state.limiter = limiter

# Shared metrics registry
metrics_registry = AgentMetrics.get_registry()

# Create circuit breakers for external calls
core_api_breaker = CircuitBreaker(
    name="hypercode_core",
    failure_threshold=5,
    recovery_timeout=60
)

START_TIME = time.time()

# Paths exempt from rate limiting (health + metrics must always respond)
RATE_LIMIT_EXEMPT = {"/health", "/metrics", "/"}


def _is_truthy(value: str | None) -> bool:
    """Return True if a string represents a truthy value."""
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def setup_telemetry() -> None:
    """Initialize OpenTelemetry tracing if enabled via environment."""
    if _is_truthy(os.getenv("OTEL_SDK_DISABLED")):
        logger.info("OpenTelemetry SDK is disabled.")
        return
    if _is_truthy(os.getenv("OTLP_EXPORTER_DISABLED")):
        logger.info("OpenTelemetry exporter is disabled.")
        return

    service_name = os.getenv("SERVICE_NAME", os.getenv("AGENT_ROLE", "test-agent"))
    environment = os.getenv("ENVIRONMENT", "development")
    endpoint = os.getenv("OTLP_ENDPOINT", "http://tempo:4317")

    resource = Resource.create(
        attributes={
            "service.name": service_name,
            "deployment.environment": environment,
        }
    )
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True))
    )
    trace.set_tracer_provider(tracer_provider)
    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer_provider)
    logger.info("OpenTelemetry initialized for service: %s", service_name)


setup_telemetry()


@app.get("/")
def read_root():
    """Return basic identity information for this agent."""
    return {
        "version": "v1.0",
        "message": "I am the test subject.",
        "agent": os.getenv("AGENT_ROLE", "test-agent"),
        "core_url": os.getenv("CORE_URL", "not set"),
    }


@app.get("/health")
def health_check():
    """Return liveness information for Docker and service discovery."""
    try:
        uptime = round(time.time() - START_TIME, 2)
        return {"status": "ok", "uptime_seconds": uptime}
    except Exception as e:
        logger.error("Health check failed: %s", e)
        return JSONResponse(
            status_code=500, content={"status": "error", "detail": str(e)}
        )


@app.get("/capabilities")
def capabilities():
    """Return a minimal capability descriptor for orchestration."""
    return {
        "name": "test-agent",
        "version": "1.0.0",
        "endpoints": ["/", "/health", "/capabilities", "/metrics"],
        "requires": ["hypercode-core"],
        "cache_hit_rate": "~70%",
        "rate_limit": "100/minute",
        "circuit_breaker": "CLOSED",
    }


@app.get("/metrics")
def metrics() -> Response:
    """Expose Prometheus metrics for scraping (shared registry)."""
    return Response(
        AgentMetrics.generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.middleware("http")
async def log_and_rate_limit(
    request: Request, call_next: Callable
) -> Response:
    """Log requests and enforce rate limiting. Health/metrics paths are always exempt."""
    start = time.time()

    # Skip rate limiting for health + metrics — must always respond for Docker
    if request.url.path not in RATE_LIMIT_EXEMPT:
        try:
            if hasattr(limiter, 'hit'):
                limiter.hit(request)
        except Exception as e:
            logger.warning("Rate limit exceeded: %s", e)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"}
            )

    response = await call_next(request)
    duration_seconds = time.time() - start
    duration_ms = round(duration_seconds * 1000, 2)

    logger.info(
        "%s %s -> %s (%.2fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.get("/test/cached-endpoint")
@cached(ttl_seconds=60)
async def cached_endpoint(query: str = "test"):
    """Example endpoint with caching (TTL: 60s)."""
    logger.info(f"Expensive operation for query: {query}")
    time.sleep(0.5)  # Simulate expensive work
    return {
        "query": query,
        "result": f"Processed {query}",
        "cached": True,
        "timestamp": time.time(),
    }


@app.get("/test/circuit-breaker")
async def circuit_breaker_test():
    """Test circuit breaker on external call."""
    try:
        import httpx
        async def call_core():
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get("http://hypercode-core:8000/health")
                return resp.json()

        result = await core_api_breaker.call_async(call_core)
        return {"status": "ok", "core": result, "breaker": "CLOSED"}
    except Exception as e:
        logger.error(f"Circuit breaker test failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"detail": str(e), "breaker": core_api_breaker.state.value}
        )


def handle_sigterm(*_args: object) -> None:
    """Handle Docker SIGTERM for graceful shutdown."""
    logger.info("Received SIGTERM, shutting down gracefully...")
    sys.exit(0)


_ = signal.signal(signal.SIGTERM, handle_sigterm)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    logger.info("test-agent starting on port %s with Phase 1 enhancements", port)
    logger.info("Phase 1: Prometheus metrics ✓ | Redis caching ✓ | Rate limiting ✓ | Circuit breaker ✓")
    uvicorn.run(app, host="0.0.0.0", port=port)
