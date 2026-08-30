"""briefing.render_markdown / _chunk_summary: pure formatting, no network."""

import briefing
from models import Paper


def _papers(n=2):
    return [
        Paper(arxiv_id=f"2608.{i:05d}", title=f"Title {i}",
              authors=[f"A{j}" for j in range(7)], summary="x" * 500,
              url=f"http://arxiv.org/abs/2608.{i:05d}", categories=["cs.AI"])
        for i in range(n)
    ]


def test_chunk_summary_truncates():
    assert briefing._chunk_summary("word " * 200).endswith("...")
    assert briefing._chunk_summary("short") == "short"


def test_render_sweep_has_window_and_picks():
    md = briefing.render_markdown("sweep", _papers(2), topic=None,
                                  window="last 7 day(s)", categories=["cs.AI"], new_count=2)
    assert "Weekly Research Brief" in md
    assert "last 7 day(s)" in md
    assert "**New papers:** 2" in md
    assert md.count("### ") == 2
    assert "et al." in md  # 7 authors -> truncated
    assert "observe-only" in md


def test_render_topic_names_topic():
    md = briefing.render_markdown("topic", _papers(1), topic="RAG graphs",
                                  window="relevance-ranked", categories=["cs.AI"], new_count=1)
    assert "Research Brief - RAG graphs" in md


def test_render_empty_is_graceful():
    md = briefing.render_markdown("sweep", [], topic=None, window="last 7 day(s)",
                                  categories=["cs.AI"], new_count=0)
    assert "No new papers" in md
    assert "### " not in md
