"""Merge-collision tests for coder-studio.

The whole point of per-task worktrees is parallel runs — but that means two
sessions can both reach REVIEW against the same base commit, then race to merge.
The first wins; the second's ``git merge --ff-only`` fails because main has
moved under it.

This file pins the exact behaviour we want in that state:

  1. The second merge attempt returns 409 with a human-readable reason.
  2. The session is left in REVIEW (not FAILED, not MERGED) — the change is
     still there on the agent branch, recoverable.
  3. The worktree is NOT deleted — the human can still inspect the diff and
     decide what to do.
  4. The first merge's commit survives on main untouched.
  5. A concurrent discard of the losing session cleans up without corrupting
     the winning commit.

These tests run against a real git repo in a temp directory — no mocks.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import main
from sessions import Session, SessionStore, Status
from worktree import Worktree, capture_diff, create_worktree, merge_worktree

KEY = "collision-test-key"


# ── helpers ────────────────────────────────────────────────────────────────────


def git(repo: Path, *args: str) -> str:
    r = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    return r.stdout.strip()


def make_repo(tmp_path: Path) -> Path:
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


def seed_session(repo: Path, filename: str, content: str, slug: str) -> Session:
    """Create a worktree with a change, advance it to REVIEW."""
    wt = create_worktree(repo, slug)
    (wt.path / filename).write_text(content, encoding="utf-8")
    s = main.store.create(f"write {filename}", wt)
    s.diff = capture_diff(wt)
    s.set_status(Status.REVIEW)
    return s


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return make_repo(tmp_path)


@pytest.fixture
def client(repo: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("HYPERCODE_API_KEY", KEY)
    monkeypatch.setenv("WORKSPACE_ROOT", str(repo))
    monkeypatch.setattr(main, "store", SessionStore())
    return TestClient(main.app)


def auth():
    return {"X-Agent-Key": KEY}


# ── 1. direct worktree layer: merge_worktree itself ───────────────────────────


def test_merge_worktree_fails_when_base_has_moved(repo: Path):
    """``merge_worktree`` raises WorktreeError when --ff-only is impossible."""
    from worktree import WorktreeError

    wt_a = create_worktree(repo, "task-a")
    wt_b = create_worktree(repo, "task-b")

    (wt_a.path / "a.py").write_text("# a\n", encoding="utf-8")
    (wt_b.path / "b.py").write_text("# b\n", encoding="utf-8")

    # Merge A — main advances.
    sha_a = merge_worktree(wt_a, message="feat: a")
    assert git(repo, "rev-parse", "HEAD") == sha_a

    # B's base is now behind main — ff-only must refuse.
    with pytest.raises(WorktreeError, match=r"(ff-only|fast-forward|merge)"):
        merge_worktree(wt_b, message="feat: b")


def test_losing_worktree_still_has_its_branch_after_collision(repo: Path):
    """The agent branch must survive the failed merge so the diff is recoverable."""
    from worktree import WorktreeError

    wt_a = create_worktree(repo, "task-a")
    wt_b = create_worktree(repo, "task-b")

    (wt_a.path / "a.py").write_text("# a\n", encoding="utf-8")
    (wt_b.path / "b.py").write_text("# b\n", encoding="utf-8")

    merge_worktree(wt_a, message="feat: a")

    with pytest.raises(WorktreeError):
        merge_worktree(wt_b, message="feat: b")

    # Branch still exists — the work is not lost.
    assert git(repo, "branch", "--list", wt_b.branch) != ""
    # The change is still visible in the diff.
    assert "b.py" in capture_diff(wt_b)


def test_winning_commit_survives_the_collision(repo: Path):
    """A's merged commit must be untouched after B's failed merge."""
    from worktree import WorktreeError

    wt_a = create_worktree(repo, "task-a")
    wt_b = create_worktree(repo, "task-b")

    (wt_a.path / "a.py").write_text("# a\n", encoding="utf-8")
    (wt_b.path / "b.py").write_text("# b\n", encoding="utf-8")

    sha_a = merge_worktree(wt_a, message="feat: a")

    with pytest.raises(WorktreeError):
        merge_worktree(wt_b, message="feat: b")

    # main still points at A's commit.
    assert git(repo, "rev-parse", "HEAD") == sha_a
    assert (repo / "a.py").exists()
    assert not (repo / "b.py").exists()


# ── 2. HTTP layer: the API returns the right status codes and session state ───


def test_second_merge_returns_409(client, repo):
    """A concurrent merge collision must surface as a 409, not a 500."""
    s_a = seed_session(repo, "a.py", "# a\n", "task-a")
    s_b = seed_session(repo, "b.py", "# b\n", "task-b")

    r_a = client.post(f"/sessions/{s_a.id}/merge", headers=auth())
    assert r_a.status_code == 200
    assert r_a.json()["status"] == "merged"

    r_b = client.post(f"/sessions/{s_b.id}/merge", headers=auth())
    assert r_b.status_code == 409


def test_losing_session_stays_in_review_after_409(client, repo):
    """A failed merge must leave the session in REVIEW so the human can retry
    or discard — not flip it to FAILED, which would make it un-discardable."""
    s_a = seed_session(repo, "a.py", "# a\n", "task-a")
    s_b = seed_session(repo, "b.py", "# b\n", "task-b")

    client.post(f"/sessions/{s_a.id}/merge", headers=auth())
    client.post(f"/sessions/{s_b.id}/merge", headers=auth())

    # Fetch the loser's current state.
    r = client.get(f"/sessions/{s_b.id}", headers=auth())
    assert r.json()["status"] == "review"


def test_losing_session_diff_still_available_after_409(client, repo):
    """The loser's diff must still be readable — the human needs to decide
    whether to start a fresh task or just discard."""
    s_a = seed_session(repo, "a.py", "# a\n", "task-a")
    s_b = seed_session(repo, "b.py", "# b\n", "task-b")

    client.post(f"/sessions/{s_a.id}/merge", headers=auth())
    client.post(f"/sessions/{s_b.id}/merge", headers=auth())

    r = client.get(f"/sessions/{s_b.id}/diff", headers=auth())
    assert "b.py" in r.json()["diff"]


def test_409_detail_is_human_readable(client, repo):
    """The error body must tell the human what happened, not dump a raw git
    error like 'exit status 128'."""
    s_a = seed_session(repo, "a.py", "# a\n", "task-a")
    s_b = seed_session(repo, "b.py", "# b\n", "task-b")

    client.post(f"/sessions/{s_a.id}/merge", headers=auth())
    r_b = client.post(f"/sessions/{s_b.id}/merge", headers=auth())

    detail = r_b.json().get("detail", "")
    # Must mention the merge failed — raw git stderr alone is not enough.
    assert "merge" in detail.lower() or "fast" in detail.lower() or "conflict" in detail.lower()


def test_discard_after_collision_cleans_up_without_corrupting_main(client, repo):
    """After a merge collision the user should be able to cleanly discard the
    losing session without touching the winning commit on main."""
    s_a = seed_session(repo, "a.py", "# a\n", "task-a")
    s_b = seed_session(repo, "b.py", "# b\n", "task-b")

    r_a = client.post(f"/sessions/{s_a.id}/merge", headers=auth())
    sha_a = r_a.json()["merge_sha"]

    client.post(f"/sessions/{s_b.id}/merge", headers=auth())  # 409
    r_discard = client.post(f"/sessions/{s_b.id}/discard", headers=auth())

    assert r_discard.status_code == 200
    assert r_discard.json()["status"] == "discarded"

    # main is untouched.
    assert git(repo, "rev-parse", "HEAD") == sha_a
    assert not (repo / "b.py").exists()


# ── 3. three-way collision: only the first wins ───────────────────────────────


def test_only_first_of_three_concurrent_merges_wins(client, repo):
    """Regression: with N sessions all at REVIEW, exactly one lands on main."""
    sessions = [
        seed_session(repo, f"task{i}.py", f"# {i}\n", f"task-{i}")
        for i in range(3)
    ]

    results = [
        client.post(f"/sessions/{s.id}/merge", headers=auth())
        for s in sessions
    ]

    codes = [r.status_code for r in results]
    assert codes.count(200) == 1
    assert codes.count(409) == 2

    # Exactly one new file on main.
    landed = [f"task{i}.py" for i in range(3) if (repo / f"task{i}.py").exists()]
    assert len(landed) == 1


# ── 4. idempotency survives a collision ───────────────────────────────────────


def test_winner_merge_is_still_idempotent_after_collision(client, repo):
    """A double-click on Merge for the winner must still be a no-op."""
    s_a = seed_session(repo, "a.py", "# a\n", "task-a")
    s_b = seed_session(repo, "b.py", "# b\n", "task-b")

    r1 = client.post(f"/sessions/{s_a.id}/merge", headers=auth())
    client.post(f"/sessions/{s_b.id}/merge", headers=auth())  # collision

    r2 = client.post(f"/sessions/{s_a.id}/merge", headers=auth())
    assert r2.status_code == 200
    assert r2.json()["merge_sha"] == r1.json()["merge_sha"]
