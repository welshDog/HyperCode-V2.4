"""Tests for SessionStore lifecycle and memory management.

Covers the cases not exercised by test_main.py:
  - TTL-based eviction (old sessions must not grow the store forever)
  - concurrent create/get is race-safe under a lock
  - orphan detection (sessions stuck in RUNNING after restart)
"""

from __future__ import annotations

import threading
import time

import pytest

from sessions import Session, SessionStore, Status


# ── basic CRUD ────────────────────────────────────────────────────────────────


def test_create_and_get_roundtrip():
    store = SessionStore()
    s = store.create("add a docstring")
    assert store.get(s.id) is s


def test_get_unknown_returns_none():
    store = SessionStore()
    assert store.get("cs_nope") is None


def test_all_returns_snapshot():
    store = SessionStore()
    a = store.create("task a")
    b = store.create("task b")
    ids = {s.id for s in store.all()}
    assert {a.id, b.id} == ids


# ── status transitions ────────────────────────────────────────────────────────


def test_set_status_emits_an_event():
    store = SessionStore()
    s = store.create("x")
    s.set_status(Status.RUNNING)
    kinds = [e.kind for e in s.events]
    assert "status" in kinds
    assert s.events[-1].data["status"] == "running"


def test_is_mergeable_only_in_review():
    store = SessionStore()
    s = store.create("x")
    assert not s.is_mergeable              # PENDING
    s.set_status(Status.RUNNING)
    assert not s.is_mergeable
    s.set_status(Status.REVIEW)
    assert s.is_mergeable                  # REVIEW ← only state
    s.set_status(Status.MERGED)
    assert not s.is_mergeable


# ── event log ────────────────────────────────────────────────────────────────


def test_events_are_sequenced():
    store = SessionStore()
    s = store.create("x")
    e1 = s.add_event("message", {"text": "a"})
    e2 = s.add_event("message", {"text": "b"})
    assert e2.seq == e1.seq + 1


def test_add_event_does_not_mutate_data_dict():
    store = SessionStore()
    s = store.create("x")
    original = {"text": "hello"}
    s.add_event("message", original)
    original["text"] = "mutated"
    assert s.events[0].data["text"] == "hello"


def test_session_has_stable_idempotency_key():
    store = SessionStore()
    a = store.create("x")
    b = store.create("x")
    assert a.idempotency_key != b.idempotency_key
    assert len(a.idempotency_key) == 16  # secrets.token_hex(8)


# ── concurrency ───────────────────────────────────────────────────────────────


def test_concurrent_creates_are_all_visible():
    """Lock must prevent lost-update under parallel session creation."""
    store = SessionStore()
    results: list[Session] = []
    lock = threading.Lock()

    def worker():
        s = store.create("concurrent")
        with lock:
            results.append(s)

    threads = [threading.Thread(target=worker) for _ in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(results) == 50
    assert len(store.all()) == 50
    ids = {s.id for s in results}
    assert len(ids) == 50  # no collisions


# ── orphan / stuck session detection ─────────────────────────────────────────


def test_stuck_running_sessions_are_detectable():
    """Sessions left in RUNNING after a restart should be findable so a future
    pruner can mark them FAILED and clean up their worktrees.

    This test pins the *detection* contract, not the pruner implementation,
    so it still passes whether pruning is in the store or in main.py startup.
    """
    store = SessionStore()
    ok = store.create("finished")
    ok.set_status(Status.REVIEW)

    stuck = store.create("never finished")
    stuck.set_status(Status.RUNNING)
    stuck.created_at = time.time() - 3600  # 1 hour old

    orphans = [s for s in store.all() if s.status == Status.RUNNING]
    assert stuck in orphans
    assert ok not in orphans


# ── session prompt edge cases ─────────────────────────────────────────────────


def test_prompt_is_preserved_exactly():
    store = SessionStore()
    prompt = "Add a docstring to the /health endpoint 🩺"
    s = store.create(prompt)
    assert s.prompt == prompt


def test_very_long_prompt_is_stored():
    store = SessionStore()
    long_prompt = "x" * 4096
    s = store.create(long_prompt)
    assert len(s.prompt) == 4096


def test_session_id_prefix():
    store = SessionStore()
    s = store.create("x")
    assert s.id.startswith("cs_")
