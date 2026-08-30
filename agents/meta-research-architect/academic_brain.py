"""Read-only arXiv research gathering.

Phase 1: no embeddings, no storage, no writes. Just fetch recent papers and
hand back structured metadata. The briefing layer turns that into prose.
"""

from __future__ import annotations

import logging

import arxiv

from models import Paper

logger = logging.getLogger(__name__)

# One shared client — arxiv.Client handles page fetching + polite rate limiting.
_client = arxiv.Client(page_size=100, delay_seconds=3.0, num_retries=3)


def _to_paper(result: arxiv.Result) -> Paper:
    return Paper(
        arxiv_id=result.get_short_id(),
        title=result.title.strip().replace("\n", " "),
        authors=[a.name for a in result.authors],
        summary=result.summary.strip().replace("\n", " "),
        published=result.published.isoformat() if result.published else "",
        url=result.entry_id,
        categories=list(result.categories),
    )


def search_topic(topic: str, max_results: int = 10, categories: list[str] | None = None) -> list[Paper]:
    """Relevance-ranked search for an ad-hoc topic."""
    query = topic
    if categories:
        cat_clause = " OR ".join(f"cat:{c}" for c in categories)
        query = f"({topic}) AND ({cat_clause})"
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
    )
    try:
        return [_to_paper(r) for r in _client.results(search)]
    except Exception:  # noqa: BLE001 - arxiv raises a grab-bag of network errors
        logger.exception("arXiv topic search failed for %r", topic)
        return []


def recent_by_categories(categories: list[str], max_results: int = 25) -> list[Paper]:
    """Newest-first sweep across the given categories (used by the scheduler)."""
    cat_clause = " OR ".join(f"cat:{c}" for c in categories)
    search = arxiv.Search(
        query=cat_clause,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )
    try:
        return [_to_paper(r) for r in _client.results(search)]
    except Exception:  # noqa: BLE001
        logger.exception("arXiv sweep failed for categories %s", categories)
        return []
