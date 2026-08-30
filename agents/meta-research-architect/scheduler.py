"""In-process APScheduler wrapper.

One interval job (the arXiv sweep) plus an optional one-shot shortly after
startup so a fresh container is not silent until the first interval fires.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
import sweep

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _job() -> None:
    try:
        result = await sweep.run_sweep()
        logger.info("scheduled sweep done: %s new paper(s)", result.new_count)
    except Exception:  # noqa: BLE001
        logger.exception("scheduled sweep raised")


def start() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(
        _job,
        "interval",
        seconds=config.UPDATE_INTERVAL_SECONDS,
        id="arxiv-sweep",
        max_instances=1,
        coalesce=True,
    )
    if config.RUN_ON_STARTUP:
        _scheduler.add_job(
            _job,
            "date",
            run_date=datetime.now(timezone.utc) + timedelta(seconds=config.STARTUP_DELAY_SECONDS),
            id="arxiv-sweep-startup",
        )
    _scheduler.start()
    logger.info(
        "scheduler started: sweep every %ss (run_on_startup=%s)",
        config.UPDATE_INTERVAL_SECONDS, config.RUN_ON_STARTUP,
    )


def shutdown() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def next_run() -> str | None:
    if _scheduler is None:
        return None
    job = _scheduler.get_job("arxiv-sweep")
    return job.next_run_time.isoformat() if job and job.next_run_time else None
