"""Gordon Tier 3 — Celery + queue metrics for Prometheus.

Exposes:
    hypercode_celery_tasks_total{task,status}  — Counter (success/failure/retry)
    hypercode_celery_task_duration_seconds{task} — Histogram
    hypercode_celery_queue_depth{queue}        — Gauge (Redis LLEN)

Wiring:
    Counters/histogram: connected via Celery signals at import time.
    Queue-depth gauge: emitted on each /metrics scrape via a custom Collector
    that reads Redis LLEN — no polling thread required.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Optional

from celery.signals import task_failure, task_postrun, task_prerun, task_retry
from prometheus_client import REGISTRY, Counter, Histogram
from prometheus_client.core import GaugeMetricFamily

logger = logging.getLogger(__name__)


CELERY_TASKS_TOTAL = Counter(
    "hypercode_celery_tasks_total",
    "Total Celery tasks by name and final status",
    ["task", "status"],
)

CELERY_TASK_DURATION = Histogram(
    "hypercode_celery_task_duration_seconds",
    "Celery task execution duration",
    ["task"],
    # Buckets tuned for agent tasks (fast cache hits to long LLM calls)
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 300),
)


# Per-process map of task_id -> start_time. Cleared on postrun. Worker-local
# state, never shared cross-process — no lock needed.
_task_start_times: dict[str, float] = {}


@task_prerun.connect
def _on_task_prerun(task_id=None, task=None, **_kwargs) -> None:
    if task_id is None:
        return
    _task_start_times[task_id] = time.perf_counter()


@task_postrun.connect
def _on_task_postrun(task_id=None, task=None, state=None, **_kwargs) -> None:
    if task_id is None:
        return
    start = _task_start_times.pop(task_id, None)
    name = getattr(task, "name", "unknown")
    if start is not None:
        CELERY_TASK_DURATION.labels(task=name).observe(time.perf_counter() - start)
    # Map Celery state to a stable label set
    status = "success" if state == "SUCCESS" else (state or "unknown").lower()
    CELERY_TASKS_TOTAL.labels(task=name, status=status).inc()


@task_failure.connect
def _on_task_failure(task_id=None, sender=None, **_kwargs) -> None:
    name = getattr(sender, "name", "unknown")
    CELERY_TASKS_TOTAL.labels(task=name, status="failure").inc()


@task_retry.connect
def _on_task_retry(request=None, sender=None, **_kwargs) -> None:
    name = getattr(sender, "name", "unknown")
    CELERY_TASKS_TOTAL.labels(task=name, status="retry").inc()


# ---------------------------------------------------------------------------
# Queue-depth collector
#
# Celery on Redis stores pending messages in a list keyed by the queue name.
# LLEN gives us pending-task backlog without consuming the messages.
# Sampled on each /metrics scrape (default 15s) — cheap, no extra threads.
# ---------------------------------------------------------------------------
QUEUES_TO_TRACK = ("main-queue", "celery")  # default queue name + our routed one


class CeleryQueueDepthCollector:
    """Reads Redis LLEN for known Celery queues on each Prometheus scrape."""

    def __init__(self, redis_url: Optional[str] = None) -> None:
        self._redis_url = redis_url or os.getenv(
            "HYPERCODE_REDIS_URL", "redis://redis:6379/0"
        )
        self._client = None  # lazy-init on first scrape

    def _get_client(self):
        if self._client is None:
            try:
                import redis as _redis_sync

                self._client = _redis_sync.Redis.from_url(
                    self._redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
            except Exception as exc:
                logger.debug(f"CeleryQueueDepthCollector: redis init failed ({exc})")
                self._client = None
        return self._client

    def collect(self):
        gauge = GaugeMetricFamily(
            "hypercode_celery_queue_depth",
            "Pending tasks in each Celery queue (Redis LLEN)",
            labels=["queue"],
        )
        client = self._get_client()
        if client is None:
            yield gauge
            return

        for queue in QUEUES_TO_TRACK:
            try:
                depth = client.llen(queue)
                gauge.add_metric([queue], float(depth))
            except Exception as exc:
                logger.debug(
                    f"CeleryQueueDepthCollector: LLEN {queue} failed ({exc})"
                )

        yield gauge


_celery_queue_collector_registered = False


def register_celery_queue_collector() -> None:
    """Register the Celery queue-depth collector exactly once."""
    global _celery_queue_collector_registered
    if _celery_queue_collector_registered:
        return
    REGISTRY.register(CeleryQueueDepthCollector())
    _celery_queue_collector_registered = True
    logger.info("CeleryQueueDepthCollector registered with Prometheus")
