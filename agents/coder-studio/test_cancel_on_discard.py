"""Discarding a RUNNING session must cancel its background agent task.

Without this, hitting Discard mid-run leaves the agent running: it keeps
spending API budget, then crashes noisily when it reaches for the worktree the
discard already removed. The fix tracks the asyncio.Task per session and cancels
it on discard.

This is a standalone file (no shared fixtures with test_main.py) so it doesn't
collide with concurrent work on the main endpoint tests.
"""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import pytest

import main
from sessions import Session, SessionStore, Status
from worktree import create_worktree

KEY = "test-key"


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    run = lambda *a: subprocess.run(["git", *a], cwd=root, check=True, capture_output=True)
    run("init", "-b", "main")
    run("config", "user.email", "t@t.t")
    run("config", "user.name", "T")
    (root / "app.py").write_text("print('hi')\n", encoding="utf-8")
    run("add", "-A")
    run("commit", "-m", "init")
    return root


@pytest.fixture(autouse=True)
def env(repo: Path, monkeypatch):
    monkeypatch.setenv("HYPERCODE_API_KEY", KEY)
    monkeypatch.setenv("WORKSPACE_ROOT", str(repo))
    monkeypatch.setattr(main, "store", SessionStore())


def _blocking_agent(started: asyncio.Event, finished: asyncio.Event):
    """A run_agent stand-in that starts, signals, then blocks forever — so we
    can catch the session mid-run and cancel it. Sets `finished` only if it is
    allowed to run to completion (it must NOT be, once cancelled)."""

    async def _run(worktree, shepherd, prompt, *, model=None, env=None, on_decision=None,
                   resolve_escalation=None):
        started.set()
        try:
            await asyncio.sleep(3600)  # never completes on its own
        finally:
            finished.set()
        if False:  # pragma: no cover - unreachable, keeps this an async generator
            yield None

    return _run


async def _run_to_status(session: Session, target: Status, timeout: float = 5.0):
    async def waiter():
        while session.status != target:
            await asyncio.sleep(0.01)
    await asyncio.wait_for(waiter(), timeout)


# --- the behaviour under test ---


async def test_discarding_a_running_session_cancels_the_agent(repo, monkeypatch):
    started, finished = asyncio.Event(), asyncio.Event()
    monkeypatch.setattr(main, "run_agent", _blocking_agent(started, finished))

    # Start a session exactly as the endpoint does.
    session = main.store.create("long task")
    task = asyncio.create_task(main._drive_agent(session, model=None, slug="cancelme"))
    main.register_task(session.id, task)  # the fix exposes this

    await asyncio.wait_for(started.wait(), 5.0)      # agent is now mid-run
    await _run_to_status(session, Status.RUNNING)

    # Discard while it's running.
    await main.discard(session.id)

    assert task.cancelled() or task.done()           # the run was stopped
    assert session.status == Status.DISCARDED
    assert session.worktree is None or not session.worktree.path.exists()


async def test_discard_leaves_no_orphan_worktree_when_cancelled(repo, monkeypatch):
    started, finished = asyncio.Event(), asyncio.Event()
    monkeypatch.setattr(main, "run_agent", _blocking_agent(started, finished))

    session = main.store.create("long task")
    task = asyncio.create_task(main._drive_agent(session, model=None, slug="orphan"))
    main.register_task(session.id, task)
    await asyncio.wait_for(started.wait(), 5.0)

    await main.discard(session.id)

    # The agent's git worktree must be gone from the repo, not left dangling.
    listed = subprocess.run(
        ["git", "worktree", "list"], cwd=repo, capture_output=True, text=True
    ).stdout
    assert listed.count("\n") == 1  # only the main working tree


async def test_discarding_before_the_agent_starts_is_still_clean(repo, monkeypatch):
    """Discard right after start (task registered, agent not yet running)."""
    started, finished = asyncio.Event(), asyncio.Event()
    monkeypatch.setattr(main, "run_agent", _blocking_agent(started, finished))

    session = main.store.create("quick bail")
    task = asyncio.create_task(main._drive_agent(session, model=None, slug="bail"))
    main.register_task(session.id, task)

    await main.discard(session.id)  # may race the worktree creation

    assert session.status == Status.DISCARDED
    assert not finished.is_set()  # the agent body never completed


async def test_completed_session_discard_is_a_noop_cancel(repo, monkeypatch):
    """Discarding an already-finished session must not error on a done task."""
    session = main.store.create("done")
    session.worktree = create_worktree(repo, "done")
    session.set_status(Status.REVIEW)
    # A task that has already finished.
    done = asyncio.create_task(asyncio.sleep(0))
    await done
    main.register_task(session.id, done)

    result = await main.discard(session.id)

    assert result.status == Status.DISCARDED.value
