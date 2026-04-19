from celery import Celery
from kombu import Exchange, Queue

from app.core.config import settings

celery_app = Celery(
    "hypercode_worker",
    broker=settings.HYPERCODE_REDIS_URL,
    backend=settings.HYPERCODE_REDIS_URL
)

# ---------------------------------------------------------------------------
# Gordon Tier 3 — Priority queues + Dead Letter Queue
#
# Three live queues separate fast/slow work so a slow task can't starve a
# fast one: workers can be scaled per-queue or pinned with --queues=.
#
#   hypercode-high   — interactive paths the user is waiting on
#   hypercode-normal — default for everything (background agent jobs)
#   hypercode-low    — opportunistic work (cache warming, batch reports)
#
# DLQ:
#   hypercode-dlq    — terminal-failure sink. Tasks land here only after
#                      max_retries is exhausted; they are NOT consumed by
#                      workers — they sit until an operator inspects/replays.
#
# Legacy `main-queue` is kept so existing producers don't break during
# rollout. New callers should use queue="hypercode-{high,normal,low}".
# ---------------------------------------------------------------------------
_hc_exchange = Exchange("hypercode", type="direct", durable=True)
_dlq_exchange = Exchange("hypercode-dlx", type="direct", durable=True)

celery_app.conf.task_queues = (
    Queue("hypercode-high",   _hc_exchange,  routing_key="hypercode.high"),
    Queue("hypercode-normal", _hc_exchange,  routing_key="hypercode.normal"),
    Queue("hypercode-low",    _hc_exchange,  routing_key="hypercode.low"),
    # DLQ — durable, never auto-consumed. Inspect with: redis-cli LRANGE hypercode-dlq 0 -1
    Queue("hypercode-dlq",    _dlq_exchange, routing_key="hypercode.dlq", durable=True),
    # Legacy
    Queue("main-queue",       _hc_exchange,  routing_key="hypercode.main"),
)

celery_app.conf.task_default_queue = "hypercode-normal"
celery_app.conf.task_default_exchange = "hypercode"
celery_app.conf.task_default_routing_key = "hypercode.normal"

celery_app.conf.task_routes = {
    # Legacy explicit routings kept until callers migrate
    "hypercode.tasks.process_agent_job": {"queue": "main-queue"},
    "hypercode.tasks.run_agent_task":    {"queue": "hypercode-normal"},
    "app.worker.test_celery":            {"queue": "main-queue"},
}

# Explicitly import the worker module so tasks are registered
celery_app.conf.imports = ('app.worker',)

# ---------------------------------------------------------------------------
# Gordon Tier 3 — Celery reliability settings
#
# task_acks_late=True
#   Tasks are acknowledged to the broker AFTER completion, not on receipt.
#   If the worker crashes mid-task, the message is re-queued automatically.
#   Essential for long-running agent tasks where losing work is costly.
#
# worker_prefetch_multiplier=1
#   Each worker only reserves 1 task at a time (instead of the default 4).
#   Prevents a slow task from blocking other queued work on the same worker.
#   Better fairness for mixed short/long agent tasks.
#
# task_soft_time_limit=300 / task_time_limit=360
#   Soft limit raises SoftTimeLimitExceeded inside the task at 5 min so the
#   handler can clean up (release DB session, mark task FAILED, etc).  Hard
#   limit kills the worker process at 6 min if soft cleanup hangs.  Together
#   these stop a runaway agent (infinite loop, stuck LLM call) from pinning
#   a worker forever and starving the queue.
# ---------------------------------------------------------------------------
celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_soft_time_limit=300,
    task_time_limit=360,
)

# Gordon Tier 3 — import for side effects: connects Celery signal handlers
# to Prometheus counters/histogram inside every worker process.
try:
    import app.observability.celery_metrics  # noqa: F401
except Exception:
    # Observability is optional — worker must still boot if metrics import fails
    pass
