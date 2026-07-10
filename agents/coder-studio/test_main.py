"""Tests for the coder-studio FastAPI service.

Three seams, tested independently so none depends on the fragile interaction of
TestClient + a fire-and-forget background task + SSE polling (which deadlocks
under the test portal even though it works under real uvicorn):

  1. ``_drive_agent``   — the run loop, as a plain awaitable, with run_agent faked
  2. ``sse_events``     — the event generator, over a hand-built session
  3. the HTTP endpoints — against sessions pre-seeded into the store

The live agent path is proven separately by smoke_gate.py.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import main
from sessions import Session, SessionStore, Status
from worktree import Worktree, create_worktree

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


def git_out(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, encoding="utf-8", errors="replace"
    ).stdout.strip()


def _assistant_text(text: str):
    """A real AssistantMessage so _drive_agent's isinstance checks fire."""
    from claude_agent_sdk import AssistantMessage, TextBlock

    return AssistantMessage(
        content=[TextBlock(text=text)],
        model="claude-haiku-4-5",
        parent_tool_use_id=None,
    )


def fake_run_agent(writes=None, *, decisions=None, fail=None):
    async def _run(worktree, shepherd, prompt, *, model=None, env=None, on_decision=None):
        for d in decisions or []:
            if on_decision:
                on_decision(d)
        if fail:
            raise RuntimeError(fail)
        for rel, content in (writes or {}).items():
            (worktree.path / rel).write_text(content, encoding="utf-8")
        yield _assistant_text("done")

    return _run


# ── 1. _drive_agent: the run loop ───────────────────────────────────────────
async def test_drive_agent_reaches_review_with_a_diff(repo, monkeypatch):
    monkeypatch.setattr(main, "run_agent", fake_run_agent({"greet.py": "print('yo')\n"}))
    wt = create_worktree(repo, "drive")
    session = Session(id="cs_x", prompt="add greet", worktree=wt)

    await main._drive_agent(session, model=None)

    assert session.status == Status.REVIEW
    assert "greet.py" in (session.diff or "")
    assert not (repo / "greet.py").exists()  # not merged
    kinds = [e.kind for e in session.events]
    assert "status" in kinds and "message" in kinds


async def test_drive_agent_creates_the_worktree_when_none(repo, monkeypatch):
    """The sandbox is built in the background run, not in the POST handler, so a
    slow checkout never blocks session creation."""
    monkeypatch.setenv("WORKSPACE_ROOT", str(repo))
    monkeypatch.setattr(main, "run_agent", fake_run_agent({"made.py": "1\n"}))
    session = Session(id="cs_lazy", prompt="build", worktree=None)  # no worktree yet

    await main._drive_agent(session, model=None, slug="lazy")

    assert session.worktree is not None  # created during the run
    assert session.status == Status.REVIEW
    kinds = [e.data.get("status") for e in session.events if e.kind == "status"]
    assert "preparing sandbox" in kinds


def test_start_session_returns_immediately_without_a_worktree(client, repo, monkeypatch):
    """POST must not block on the worktree checkout — it returns pending at once."""
    # run_agent is slow/never here; we only assert the POST itself is instant + pending.
    monkeypatch.setattr(main, "run_agent", fake_run_agent({"x.py": "1\n"}))
    r = client.post("/sessions", json={"prompt": "x", "slug": "instant"}, headers=auth())
    assert r.status_code == 200
    assert r.json()["status"] == Status.PENDING.value
    assert r.json()["diff"] is None


async def test_drive_agent_records_decisions(repo, monkeypatch):
    monkeypatch.setattr(
        main,
        "run_agent",
        fake_run_agent({"a.py": "1\n"}, decisions=[{"tool": "Write", "decision": "ALLOW"}]),
    )
    wt = create_worktree(repo, "dec")
    session = Session(id="cs_d", prompt="x", worktree=wt)

    await main._drive_agent(session, model=None)

    decisions = [e for e in session.events if e.kind == "decision"]
    assert decisions and decisions[0].data["decision"] == "ALLOW"


async def test_drive_agent_failure_is_reported_not_raised(repo, monkeypatch):
    monkeypatch.setattr(main, "run_agent", fake_run_agent(fail="kaboom"))
    wt = create_worktree(repo, "boom")
    session = Session(id="cs_f", prompt="x", worktree=wt)

    await main._drive_agent(session, model=None)  # must not raise

    assert session.status == Status.FAILED
    errors = [e for e in session.events if e.kind == "error"]
    assert errors and "kaboom" in errors[0].data["error"]


# ── 2. sse_events: the event generator ──────────────────────────────────────
async def test_sse_replays_all_events_then_ends(repo):
    wt = Worktree(repo=repo, path=repo, branch="b", base="main")
    session = Session(id="cs_s", prompt="x", worktree=wt)
    session.add_event("decision", {"decision": "ALLOW"})
    session.set_status(Status.REVIEW)

    chunks = [c async for c in main.sse_events(session, poll=0.0)]
    body = "".join(chunks)

    assert "event: decision" in body
    assert '"decision": "ALLOW"' in body
    assert body.rstrip().endswith("event: end\ndata: {}")


# ── 3. HTTP endpoints against pre-seeded sessions ───────────────────────────
@pytest.fixture
def client(repo: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("HYPERCODE_API_KEY", KEY)
    monkeypatch.setenv("WORKSPACE_ROOT", str(repo))
    monkeypatch.setattr(main, "store", SessionStore())
    return TestClient(main.app)


def seed_reviewable(repo: Path, slug="seed") -> Session:
    """A session whose worktree already contains a change, sitting in REVIEW."""
    wt = create_worktree(repo, slug)
    (wt.path / "new.py").write_text("print('new')\n", encoding="utf-8")
    session = main.store.create("do the thing", wt)
    from worktree import capture_diff

    session.diff = capture_diff(wt)
    session.set_status(Status.REVIEW)
    return session


def auth():
    return {"X-Agent-Key": KEY}


def test_health_needs_no_key(client):
    assert client.get("/health").status_code == 200


def test_start_requires_the_agent_key(client):
    assert client.post("/sessions", json={"prompt": "x"}).status_code == 401
    assert client.post("/sessions", json={"prompt": "x"}, headers={"X-Agent-Key": "no"}).status_code == 401


def test_get_diff_returns_the_captured_diff(client, repo):
    s = seed_reviewable(repo)
    body = client.get(f"/sessions/{s.id}/diff", headers=auth()).json()
    assert "new.py" in body["diff"]


def test_merge_lands_the_change_and_is_idempotent(client, repo):
    s = seed_reviewable(repo)

    first = client.post(f"/sessions/{s.id}/merge", headers=auth()).json()
    assert first["status"] == Status.MERGED.value and first["merge_sha"]
    assert (repo / "new.py").read_text(encoding="utf-8") == "print('new')\n"
    assert git_out(repo, "rev-parse", "HEAD") == first["merge_sha"]

    second = client.post(f"/sessions/{s.id}/merge", headers=auth()).json()
    assert second["merge_sha"] == first["merge_sha"]  # replay, not double-apply


def test_cannot_merge_a_failed_session(client, repo):
    wt = create_worktree(repo, "failed")
    s = main.store.create("x", wt)
    s.set_status(Status.FAILED)

    assert client.post(f"/sessions/{s.id}/merge", headers=auth()).status_code == 409


def test_discard_removes_the_worktree_without_merging(client, repo):
    s = seed_reviewable(repo, "junk")

    out = client.post(f"/sessions/{s.id}/discard", headers=auth()).json()

    assert out["status"] == Status.DISCARDED.value
    assert not (repo / "new.py").exists()
    assert git_out(repo, "status", "--porcelain") == ""


def test_missing_session_is_404(client):
    assert client.get("/sessions/cs_nope", headers=auth()).status_code == 404
    assert client.post("/sessions/cs_nope/merge", headers=auth()).status_code == 404
    assert client.post("/sessions/cs_nope/discard", headers=auth()).status_code == 404
