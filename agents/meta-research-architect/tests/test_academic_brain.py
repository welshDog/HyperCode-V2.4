"""academic_brain: arXiv results map to Paper; network errors degrade to []."""

from datetime import datetime, timezone

import academic_brain


class _FakeAuthor:
    def __init__(self, name):
        self.name = name


class _FakeResult:
    def __init__(self, i):
        self.title = f"Paper {i}\nwith a wrapped title"
        self.authors = [_FakeAuthor(f"Author {j}") for j in range(6)]
        self.summary = "Summary text.\nSecond line."
        self.published = datetime(2026, 8, 1, tzinfo=timezone.utc)
        self.entry_id = f"http://arxiv.org/abs/2608.{i:05d}"
        self.categories = ["cs.AI", "cs.LG"]

    def get_short_id(self):
        return self.entry_id.rsplit("/", 1)[-1]


def test_search_topic_maps_results(monkeypatch):
    monkeypatch.setattr(academic_brain._client, "results",
                        lambda search: iter([_FakeResult(i) for i in range(3)]))
    papers = academic_brain.search_topic("agent orchestration", max_results=3)
    assert len(papers) == 3
    p = papers[0]
    assert p.arxiv_id == "2608.00000"
    assert "\n" not in p.title and "\n" not in p.summary
    assert len(p.authors) == 6
    assert p.url.startswith("http://arxiv.org/abs/")


def test_search_topic_swallows_errors(monkeypatch):
    def _boom(_search):
        raise ConnectionError("arxiv down")

    monkeypatch.setattr(academic_brain._client, "results", _boom)
    assert academic_brain.search_topic("anything") == []


def test_recent_by_categories_swallows_errors(monkeypatch):
    def _boom(_search):
        raise TimeoutError("slow")

    monkeypatch.setattr(academic_brain._client, "results", _boom)
    assert academic_brain.recent_by_categories(["cs.AI"]) == []
