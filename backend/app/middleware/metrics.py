import logging
import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import (
    Counter,
    Histogram,
    REGISTRY,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from prometheus_client.core import GaugeMetricFamily

logger = logging.getLogger(__name__)

REQUEST_COUNT = Counter(
    "hypercode_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

REQUEST_LATENCY = Histogram(
    "hypercode_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
)


# ---------------------------------------------------------------------------
# Gordon Tier 3 — SQLAlchemy connection-pool collector
#
# Why a custom Collector instead of plain Gauges:
#   The pool's internal counters change on every checkout/checkin. Polling
#   them on each /metrics scrape (rather than on every DB call) gives
#   accurate, lock-free numbers with zero hot-path overhead.
#
# Emitted series (per engine, label `engine`=sync|async):
#   hypercode_db_pool_size           — configured pool size
#   hypercode_db_pool_checked_out    — connections currently in use
#   hypercode_db_pool_checked_in     — idle connections in pool
#   hypercode_db_pool_overflow       — connections beyond pool_size
#
# When checked_out approaches pool_size + max_overflow, requests start
# blocking on pool_timeout — alert before that happens.
# ---------------------------------------------------------------------------
class DBPoolCollector:
    """Prometheus collector that snapshots SQLAlchemy pool state on scrape."""

    def collect(self):
        try:
            from app.db.session import engine as sync_engine, async_engine
        except Exception as exc:
            logger.debug(f"DBPoolCollector: engine import failed ({exc})")
            return

        size = GaugeMetricFamily(
            "hypercode_db_pool_size",
            "Configured size of the SQLAlchemy connection pool",
            labels=["engine"],
        )
        checked_out = GaugeMetricFamily(
            "hypercode_db_pool_checked_out",
            "Connections currently checked out of the pool",
            labels=["engine"],
        )
        checked_in = GaugeMetricFamily(
            "hypercode_db_pool_checked_in",
            "Idle connections currently in the pool",
            labels=["engine"],
        )
        overflow = GaugeMetricFamily(
            "hypercode_db_pool_overflow",
            "Connections opened beyond pool_size (overflow)",
            labels=["engine"],
        )

        for label, eng in (("sync", sync_engine), ("async", async_engine)):
            if eng is None:
                continue
            try:
                pool = eng.pool
                size.add_metric([label], float(pool.size()))
                checked_out.add_metric([label], float(pool.checkedout()))
                checked_in.add_metric([label], float(pool.checkedin()))
                overflow.add_metric([label], float(pool.overflow()))
            except Exception as exc:
                logger.debug(f"DBPoolCollector: {label} engine read failed ({exc})")

        yield size
        yield checked_out
        yield checked_in
        yield overflow


_db_pool_collector_registered = False


def register_db_pool_collector() -> None:
    """Register the DB-pool collector exactly once. Safe to call repeatedly."""
    global _db_pool_collector_registered
    if _db_pool_collector_registered:
        return
    REGISTRY.register(DBPoolCollector())
    _db_pool_collector_registered = True
    logger.info("DBPoolCollector registered with Prometheus")


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start

        endpoint = request.url.path
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=endpoint,
            status_code=response.status_code,
        ).inc()
        REQUEST_LATENCY.labels(method=request.method, endpoint=endpoint).observe(duration)

        return response


async def metrics_endpoint(request: Request) -> Response:
    """Expose /metrics for Prometheus scraping."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
