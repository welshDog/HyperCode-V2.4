"""Prometheus metrics initialization for hyper-auto-assistant."""

from fastapi import Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)

REGISTRY = CollectorRegistry()

route_requests_total = Counter(
    "hyper_auto_assistant_route_requests_total",
    "Total /route requests by detected intent and outcome",
    ["intent", "outcome"],
    registry=REGISTRY,
)

route_duration_seconds = Histogram(
    "hyper_auto_assistant_route_duration_seconds",
    "End-to-end /route processing duration in seconds",
    registry=REGISTRY,
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

downstream_errors_total = Counter(
    "hyper_auto_assistant_downstream_errors_total",
    "Errors talking to super-hyper-broski-agent",
    ["kind"],
    registry=REGISTRY,
)


def init_metrics(app):
    """Expose /metrics on the given FastAPI app."""

    @app.get("/metrics")
    def metrics():
        return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
