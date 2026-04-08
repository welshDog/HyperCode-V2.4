"""Prometheus metrics initialization for healer-agent."""
from prometheus_client import Counter, Histogram, make_asgi_app
from fastapi import FastAPI
from starlette.routing import Mount

# Metrics
REQUESTS_TOTAL = Counter(
    "healer_requests_total",
    "Total requests to healer agent",
    ["method", "endpoint", "status"]
)

REQUEST_DURATION = Histogram(
    "healer_request_duration_seconds",
    "Request duration in seconds",
    ["method", "endpoint"]
)

HEAL_ATTEMPTS = Counter(
    "healer_heal_attempts_total",
    "Total healing attempts",
    ["agent", "result"]
)

CIRCUIT_BREAKER_STATE = Counter(
    "healer_circuit_breaker_state_changes_total",
    "Circuit breaker state transitions",
    ["agent", "state"]
)


def init_metrics(app: FastAPI) -> None:
    """Mount /metrics endpoint on the FastAPI app."""
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)
