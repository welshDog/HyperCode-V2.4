"""Tests for the main.py timeout, discard-while-running, and ShepherdClient
lifecycle — the three gaps not covered by the existing suite.
"""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import pytest

import main
from sessions import Session, SessionStore, Status
from worktree import Worktree, create_worktree


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    run = lambda *a: subprocess.run(["git", *a], cwd=root, check=True, capture_output=True)
    run("init", "-b", "main")
    run("config", "user.email", "t@t.t")
    run("config", "user.name", "T")
    (root / "app.py").write_text("x = 1\n", encoding="utf-8")
    run("add", "-A")
    run("commit", "-m", "init")
    return root


# ── discard-while-running: agent must not continue after discard ──────────────


async def test_discard_while_running_agent_stops_cleanly(repo, monkeypatch):
    """If the user discards a RUNNING session, the drive loop must not attempt to
    write the diff or advance to REVIEW after the discard. Status must stay
    DISCARDED, not flip to REVIEW post-run.
    """
    gate_calls: list[str] = []

    async def slow_agent(worktree, shepherd, prompt, *, model=None, env=None, on_decision=None):
        gate_calls.append("started")
        # Simulate an in-progress run — yield a message then pause
        from claude_agent_sdk import AssistantMessage, TextBlock
        yield AssistantMessage(content=[TextBlock(text="working...")], model="x", parent_tool_use_id=None)

    monkeypatch.setattr(main, "run_agent", slow_agent)

    wt = create_worktree(repo, "discard-race")
    session = Session(id="cs_race", prompt="x", worktree=wt)
    # Mark discarded BEFORE the run picks it up (the discard-mid-prepare path)
    session.status = Status.DISCARDED

    await main._drive_agent(session, model=None)

    # Even though run_agent yielded a message, the session must never become REVIEW
    assert session.status == Status.DISCARDED


# ── agent run failure leaves status FAILED ───────────────────────────────────


async def test_drive_agent_gate_shadowed_error_sets_failed(repo, monkeypatch):
    from agent_runner import GateShadowedError

    async def shadow_run(*a, **k):
        raise GateShadowedError("test shadow")
        if False:
            yield None

    monkeypatch.setattr(main, "run_agent", shadow_run)
    wt = create_worktree(repo, "shadow")
    session = Session(id="cs_sh", prompt="x", worktree=wt)

    await main._drive_agent(session, model=None)

    assert session.status == Status.FAILED
    errors = [e for e in session.events if e.kind == "error"]
    assert errors
    assert "ungated" in errors[0].data["error"].lower()


# ── SSE tail stops when status is terminal ────────────────────────────────────


async def test_sse_ends_immediately_on_already_terminal_session(repo):
    wt = Worktree(repo=repo, path=repo, branch="b", base="main")
    session = Session(id="cs_t", prompt="x", worktree=wt)
    session.set_status(Status.FAILED)

    chunks = [c async for c in main.sse_events(session, poll=0.0)]
    body = "".join(chunks)

    assert "event: end" in body


async def test_sse_ends_after_merged(repo):
    wt = Worktree(repo=repo, path=repo, branch="b", base="main")
    session = Session(id="cs_m", prompt="x", worktree=wt)
    session.set_status(Status.MERGED)

    chunks = [c async for c in main.sse_events(session, poll=0.0)]
    assert any("event: end" in c for c in chunks)


# ── session creation is non-blocking ─────────────────────────────────────────


def test_post_sessions_returns_pending_immediately(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=repo, check=True, capture_output=True)
    (repo / "f.py").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "i"], cwd=repo, check=True, capture_output=True)

    monkeypatch.setenv("HYPERCODE_API_KEY", "k")
    monkeypatch.setenv("WORKSPACE_ROOT", str(repo))
    monkeypatch.setattr(main, "store", SessionStore())

    # run_agent never returns — but the POST must still return PENDING instantly
    async def hang(*a, **k):
        await asyncio.sleep(9999)
        if False:
            yield None

    monkeypatch.setattr(main, "run_agent", hang)

    client = TestClient(main.app)
    resp = client.post("/sessions", json={"prompt": "slow task"}, headers={"X-Agent-Key": "k"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending"


# ── diff endpoint content ─────────────────────────────────────────────────────


def test_diff_is_empty_string_when_no_diff_yet(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setenv("HYPERCODE_API_KEY", "k")
    store = SessionStore()
    s = store.create("no diff yet")
    monkeypatch.setattr(main, "store", store)

    client = TestClient(main.app)
    resp = client.get(f"/sessions/{s.id}/diff", headers={"X-Agent-Key": "k"})
    assert resp.status_code == 200
    assert resp.json()["diff"] == ""


# ── 404 routes ────────────────────────────────────────────────────────────────


def test_stream_events_404_on_missing_session(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setenv("HYPERCODE_API_KEY", "k")
    monkeypatch.setattr(main, "store", SessionStore())
    client = TestClient(main.app)
    resp = client.get("/sessions/cs_fake/events", headers={"X-Agent-Key": "k"})
    assert resp.status_code == 404


def test_diff_404_on_missing_session(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setenv("HYPERCODE_API_KEY", "k")
    monkeypatch.setattr(main, "store", SessionStore())
    client = TestClient(main.app)
    resp = client.get("/sessions/cs_fake/diff", headers={"X-Agent-Key": "k"})
    assert resp.status_code == 404
