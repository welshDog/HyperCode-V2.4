"""Prometheus metrics initialization for test-agent."""

from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest
from fastapi import Response
from prometheus_client import CONTENT_TYPE_LATEST

# Create registry
REGISTRY = CollectorRegistry()

# Define metrics
agent_requests_total = Counter(
    "test_agent_requests_total",
    "Total requests received",
    ["method", "endpoint", "status"],
    registry=REGISTRY,
)

agent_request_duration_seconds = Histogram(
    "test_agent_request_duration_seconds",
    "Request duration in seconds",
    ["method", "endpoint"],
    registry=REGISTRY,
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)

agent_info = Counter(
    "test_agent_info",
    "Agent info",
    ["version", "name"],
    registry=REGISTRY,
)


def init_metrics(app):
    """Initialize metrics endpoint on FastAPI app."""
    @app.get("/metrics")
    def metrics():
        return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
