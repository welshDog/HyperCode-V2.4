"""Gordon Tier 3 — Dead Letter Queue helper.

Sends terminally-failed task envelopes to ``hypercode-dlq`` for offline
inspection. Workers do NOT consume this queue — it is operator-only.

Inspect:
    redis-cli LRANGE hypercode-dlq 0 -1

Replay (after fixing root cause):
    Read the JSON, then re-enqueue with the original task signature.
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


def _safe_json(value: Any) -> Any:
    """Coerce arbitrary values into something json.dumps can handle."""
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return repr(value)
