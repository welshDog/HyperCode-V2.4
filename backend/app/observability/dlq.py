"""Gordon Tier 3 — Dead Letter Queue helper.

Sends terminally-failed task envelopes to ``hypercode-dlq`` for offline
inspection. Workers do NOT consume this queue — it is operator-only.

Inspect:
    redis-cli LRANGE hypercode-dlq 0 -1

Or hit the operator API:
    GET    /api/v1/ops/dlq/stats
    GET    /api/v1/ops/dlq?limit=50
    POST   /api/v1/ops/dlq/replay  (body: {"task_id": "..."} or {"index": 0})
    DELETE /api/v1/ops/dlq          (purge everything)
    DELETE /api/v1/ops/dlq/{task_id}
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

DLQ_QUEUE = "hypercode-dlq"
_REDIS_URL = os.getenv("HYPERCODE_REDIS_URL", "redis://redis:6379/0")

_redis_client = None  # lazy


def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis as _redis_sync

        _redis_client = _redis_sync.Redis.from_url(
            _REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    except Exception as exc:
        logger.warning(f"DLQ: redis init failed ({exc})")
        _redis_client = None
    return _redis_client


def send_to_dlq(
    task_name: str,
    args: Any,
    kwargs: dict[str, Any],
    error: str,
    *,
    task_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> bool:
    """Push a JSON envelope describing a failed task onto the DLQ.

    Returns True if the envelope was written, False otherwise. Never raises —
    DLQ failures must not mask the original task failure.
    """
    client = _get_redis()
    if client is None:
        return False

    envelope = {
        "task_name": task_name,
        "task_id": task_id,
        "args": _safe_json(args),
        "kwargs": _safe_json(kwargs),
        "error": str(error)[:2000],
        "failed_at_unix": int(time.time()),
    }
    if extra:
        envelope["extra"] = _safe_json(extra)

    try:
        # LPUSH so the newest failure is at index 0 (LRANGE shows newest first)
        client.lpush(DLQ_QUEUE, json.dumps(envelope, default=str))
        # Cap the queue at 10k entries to bound Redis memory
        client.ltrim(DLQ_QUEUE, 0, 9999)
        logger.error(
            f"[DLQ] {task_name} task_id={task_id} pushed to {DLQ_QUEUE} (error={error!s:.120})"
        )
        return True
    except Exception as exc:
        logger.warning(f"DLQ: lpush failed ({exc}) — task envelope dropped")
        return False


# ---------------------------------------------------------------------------
# Operator helpers — list / replay / purge
# ---------------------------------------------------------------------------

def list_envelopes(limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    """Return up to `limit` DLQ envelopes, newest first.

    Each envelope is decorated with an `index` field (its position in the
    Redis list) so operators can replay by index without parsing task_id.
    """
    client = _get_redis()
    if client is None:
        return []
    try:
        stop = offset + max(limit - 1, 0)
        raw = client.lrange(DLQ_QUEUE, offset, stop)
    except Exception as exc:
        logger.warning(f"DLQ: lrange failed ({exc})")
        return []

    out: list[dict[str, Any]] = []
    for i, item in enumerate(raw):
        env = _decode(item)
        if env is None:
            continue
        env["index"] = offset + i
        out.append(env)
    return out


def stats() -> dict[str, Any]:
    """Return DLQ size + oldest/newest timestamps for the dashboard + alerts."""
    client = _get_redis()
    if client is None:
        return {"queue": DLQ_QUEUE, "size": 0, "available": False}
    try:
        size = int(client.llen(DLQ_QUEUE))
    except Exception as exc:
        logger.warning(f"DLQ: llen failed ({exc})")
        return {"queue": DLQ_QUEUE, "size": 0, "available": False}

    newest_ts: int | None = None
    oldest_ts: int | None = None
    if size > 0:
        try:
            head = _decode(client.lindex(DLQ_QUEUE, 0))
            tail = _decode(client.lindex(DLQ_QUEUE, -1))
            if head:
                newest_ts = int(head.get("failed_at_unix") or 0) or None
            if tail:
                oldest_ts = int(tail.get("failed_at_unix") or 0) or None
        except Exception:
            pass

    now = int(time.time())
    return {
        "queue": DLQ_QUEUE,
        "size": size,
        "available": True,
        "newest_failed_at_unix": newest_ts,
        "oldest_failed_at_unix": oldest_ts,
        "oldest_age_seconds": (now - oldest_ts) if oldest_ts else None,
    }


def purge_all() -> int:
    """Delete every envelope. Returns the count removed."""
    client = _get_redis()
    if client is None:
        return 0
    try:
        size = int(client.llen(DLQ_QUEUE))
        client.delete(DLQ_QUEUE)
        logger.warning(f"[DLQ] purged {size} envelopes")
        return size
    except Exception as exc:
        logger.warning(f"DLQ: purge failed ({exc})")
        return 0


def remove_by_task_id(task_id: str) -> int:
    """Remove every envelope whose task_id matches. Returns count removed."""
    if not task_id:
        return 0
    client = _get_redis()
    if client is None:
        return 0
    removed = 0
    try:
        for item in client.lrange(DLQ_QUEUE, 0, -1):
            env = _decode(item)
            if env and env.get("task_id") == task_id:
                removed += int(client.lrem(DLQ_QUEUE, 0, item))
    except Exception as exc:
        logger.warning(f"DLQ: remove_by_task_id failed ({exc})")
    if removed:
        logger.info(f"[DLQ] removed {removed} envelope(s) for task_id={task_id}")
    return removed


def replay(
    *,
    task_id: str | None = None,
    index: int | None = None,
    queue: str | None = None,
) -> dict[str, Any]:
    """Re-enqueue a failed task back onto Celery.

    Looks the envelope up by `task_id` (preferred) or list `index`. Uses
    `celery_app.send_task` with the original task name + args + kwargs,
    routing to `queue` if given, else the task's configured default queue.

    On success, removes the envelope from the DLQ. Returns a dict with
    `replayed: bool`, `new_task_id`, and `error` if any.
    """
    client = _get_redis()
    if client is None:
        return {"replayed": False, "error": "redis unavailable"}

    envelope: dict[str, Any] | None = None
    raw_item: str | None = None

    try:
        if task_id is not None:
            for item in client.lrange(DLQ_QUEUE, 0, -1):
                env = _decode(item)
                if env and env.get("task_id") == task_id:
                    envelope = env
                    raw_item = item
                    break
        elif index is not None:
            item = client.lindex(DLQ_QUEUE, index)
            if item is not None:
                envelope = _decode(item)
                raw_item = item
    except Exception as exc:
        return {"replayed": False, "error": f"lookup failed: {exc}"}

    if envelope is None:
        return {"replayed": False, "error": "envelope not found"}

    task_name = envelope.get("task_name")
    if not task_name:
        return {"replayed": False, "error": "envelope missing task_name"}

    args = envelope.get("args") or []
    if not isinstance(args, (list, tuple)):
        args = [args]
    kwargs = envelope.get("kwargs") or {}
    if not isinstance(kwargs, dict):
        kwargs = {}

    try:
        from app.core.celery_app import celery_app
    except Exception as exc:
        return {"replayed": False, "error": f"celery_app import failed: {exc}"}

    try:
        send_kwargs: dict[str, Any] = {"args": list(args), "kwargs": kwargs}
        if queue:
            send_kwargs["queue"] = queue
        async_result = celery_app.send_task(task_name, **send_kwargs)
        new_id = getattr(async_result, "id", None)
    except Exception as exc:
        return {"replayed": False, "error": f"send_task failed: {exc}"}

    try:
        if raw_item is not None:
            client.lrem(DLQ_QUEUE, 0, raw_item)
    except Exception as exc:
        logger.warning(f"DLQ: replay succeeded but lrem failed ({exc})")

    logger.info(
        f"[DLQ] replayed task={task_name} old_task_id={envelope.get('task_id')} new_task_id={new_id}"
    )
    return {
        "replayed": True,
        "task_name": task_name,
        "new_task_id": new_id,
        "old_task_id": envelope.get("task_id"),
        "queue": queue,
    }


def _decode(item: str | None) -> dict[str, Any] | None:
    if item is None:
        return None
    try:
        value = json.loads(item)
        return value if isinstance(value, dict) else None
    except (TypeError, ValueError):
        return None


def _safe_json(value: Any) -> Any:
    """Coerce arbitrary values into something json.dumps can handle."""
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return repr(value)
