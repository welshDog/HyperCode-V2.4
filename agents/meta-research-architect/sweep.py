"""The one job this agent actually does in Phase 1:

  poll arXiv -> drop the papers it has not seen before -> brief -> fan out.

`seen` de-dup uses a Redis set so restarts do not re-announce old papers. If
Redis is unavailable the sweep still runs (it just cannot de-dup).
"""

from __future__ import annotations

import logging
from datetime import timedelta

import academic_brain
import briefing
import config
from models import BriefResult, Paper

logger = logging.getLogger(__name__)


async def _filter_unseen(papers: list[Paper]) -> list[Paper]:
    if not papers:
        return []
    try:
        import redis.asyncio as aioredis
    except ImportError:  # pragma: no cover
        return papers
    client = aioredis.from_url(config.REDIS_URL, socket_connect_timeout=3, socket_timeout=3)
    try:
        ids = [p.arxiv_id for p in papers]
        already = await client.smembers(config.REDIS_SEEN_KEY)
        already = {x.decode() if isinstance(x, bytes) else x for x in already}
        fresh = [p for p in papers if p.arxiv_id not in already]
        if fresh:
            await client.sadd(config.REDIS_SEEN_KEY, *[p.arxiv_id for p in fresh])
        return fresh
    except Exception as exc:  # noqa: BLE001
        logger.warning("seen-set de-dup unavailable (%s); announcing all", exc)
        return papers
    finally:
        await client.aclose()


async def run_sweep() -> BriefResult:
    """Scheduled sweep across the configured categories."""
    window_days = max(1, round(config.UPDATE_INTERVAL_SECONDS / 86400))
    window = f"last {window_days} day(s)"
    found = academic_brain.recent_by_categories(
        config.ARXIV_CATEGORIES, max_results=config.MAX_RESULTS_PER_QUERY
    )
    fresh = await _filter_unseen(found)
    picks = fresh[: config.TOP_PICKS]

    md = briefing.render_markdown(
        "sweep", picks, topic=None, window=window,
        categories=config.ARXIV_CATEGORIES, new_count=len(fresh),
    )
    result = BriefResult(
        kind="sweep", window=window, categories=config.ARXIV_CATEGORIES,
        new_count=len(fresh), papers=picks, markdown=md,
    )
    return await briefing.deliver(result)


async def run_topic(topic: str, max_sources: int, categories: list[str] | None) -> BriefResult:
    """Ad-hoc, on-demand brief for a single topic."""
    cats = categories or config.ARXIV_CATEGORIES
    papers = academic_brain.search_topic(topic, max_results=max_sources, categories=cats)
    md = briefing.render_markdown(
        "topic", papers, topic=topic, window="relevance-ranked",
        categories=cats, new_count=len(papers),
    )
    result = BriefResult(
        kind="topic", topic=topic, window="relevance-ranked",
        categories=cats, new_count=len(papers), papers=papers, markdown=md,
    )
    return await briefing.deliver(result)
