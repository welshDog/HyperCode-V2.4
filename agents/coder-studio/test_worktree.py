"""Unit tests for the coder-studio git worktree sandbox.

These run against real git in a real temp repo — no mocks. The invariant that
matters most is that nothing an agent does inside a worktree can reach the
user's working tree until a merge is explicitly requested.
"""

import subprocess
from pathlib import Path

import pytest

from worktree import (
    WorktreeEscapeError,
    capture_diff,
    create_worktree,
    discard_worktree,
    merge_worktree,
    resolve_within,
)


def git(repo: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    )
    return out.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A real git repo with one commit on the default branch."""
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "test@hyperfocus.zone")
    git(root, "config", "user.name", "BROski Test")
    (root / "app.py").write_text("print('hello')\n", encoding="utf-8")
    git(root, "add", "app.py")
    git(root, "commit", "-m", "initial")
    return root


def test_create_worktree_leaves_main_tree_clean(repo: Path):
    wt = create_worktree(repo, "add-docstring")

    assert wt.path.is_dir()
    assert wt.path != repo
    assert git(repo, "status", "--porcelain") == ""


def test_branch_name_is_namespaced_and_unique(repo: Path):
    a = create_worktree(repo, "add-docstring")
    b = create_worktree(repo, "add-docstring")

    assert a.branch.startswith("agent/add-docstring-")
    assert a.branch != b.branch


def test_agent_writes_do_not_reach_the_main_tree(repo: Path):
    wt = create_worktree(repo, "add-feature")

    (wt.path / "app.py").write_text("print('changed')\n", encoding="utf-8")
    (wt.path / "new_file.py").write_text("# brand new\n", encoding="utf-8")

    assert (repo / "app.py").read_text(encoding="utf-8") == "print('hello')\n"
    assert not (repo / "new_file.py").exists()
    assert git(repo, "status", "--porcelain") == ""


def test_capture_diff_shows_edits_and_new_files(repo: Path):
    wt = create_worktree(repo, "add-feature")
    (wt.path / "app.py").write_text("print('changed')\n", encoding="utf-8")
    (wt.path / "new_file.py").write_text("# brand new\n", encoding="utf-8")

    diff = capture_diff(wt)

    assert "-print('hello')" in diff
    assert "+print('changed')" in diff
    assert "new_file.py" in diff
    assert "+# brand new" in diff


def test_capture_diff_is_empty_when_agent_changed_nothing(repo: Path):
    wt = create_worktree(repo, "noop")

    assert capture_diff(wt) == ""


def test_capture_diff_does_not_commit(repo: Path):
    """Preview must have no side effects — the branch tip must not move."""
    wt = create_worktree(repo, "add-feature")
    tip_before = git(repo, "rev-parse", wt.branch)
    (wt.path / "app.py").write_text("print('changed')\n", encoding="utf-8")

    capture_diff(wt)
    capture_diff(wt)  # idempotent

    assert git(repo, "rev-parse", wt.branch) == tip_before


def test_merge_lands_the_change_on_the_base_branch(repo: Path):
    wt = create_worktree(repo, "add-feature")
    (wt.path / "app.py").write_text("print('changed')\n", encoding="utf-8")
    (wt.path / "new_file.py").write_text("# brand new\n", encoding="utf-8")

    sha = merge_worktree(wt, message="feat: change app")

    assert git(repo, "rev-parse", "HEAD") == sha
    assert (repo / "app.py").read_text(encoding="utf-8") == "print('changed')\n"
    assert (repo / "new_file.py").exists()
    assert git(repo, "status", "--porcelain") == ""


def test_merge_with_no_changes_returns_none_and_moves_nothing(repo: Path):
    wt = create_worktree(repo, "noop")
    head_before = git(repo, "rev-parse", "HEAD")

    assert merge_worktree(wt, message="feat: nothing") is None
    assert git(repo, "rev-parse", "HEAD") == head_before


def test_discard_removes_worktree_and_branch(repo: Path):
    wt = create_worktree(repo, "abandoned")
    (wt.path / "app.py").write_text("print('junk')\n", encoding="utf-8")

    discard_worktree(wt)

    assert not wt.path.exists()
    assert wt.branch not in git(repo, "branch", "--list", wt.branch)
    assert (repo / "app.py").read_text(encoding="utf-8") == "print('hello')\n"
    assert git(repo, "status", "--porcelain") == ""


def test_discard_after_merge_leaves_the_merged_commit(repo: Path):
    wt = create_worktree(repo, "keeper")
    (wt.path / "app.py").write_text("print('changed')\n", encoding="utf-8")
    sha = merge_worktree(wt, message="feat: keep me")

    discard_worktree(wt)

    assert git(repo, "rev-parse", "HEAD") == sha
    assert not wt.path.exists()


# --- Path containment: the last line of defence before the Shepherd ---


def test_resolve_within_accepts_a_path_inside_the_worktree(repo: Path):
    wt = create_worktree(repo, "scoped")

    assert resolve_within(wt, "app.py") == (wt.path / "app.py").resolve()
    assert resolve_within(wt, "pkg/mod.py") == (wt.path / "pkg" / "mod.py").resolve()


def test_resolve_within_rejects_dotdot_escape(repo: Path):
    wt = create_worktree(repo, "scoped")

    with pytest.raises(WorktreeEscapeError):
        resolve_within(wt, "../../../etc/passwd")


def test_resolve_within_rejects_absolute_path_outside(repo: Path):
    wt = create_worktree(repo, "scoped")

    with pytest.raises(WorktreeEscapeError):
        resolve_within(wt, str(repo / "app.py"))


def test_resolve_within_rejects_symlink_escape(repo: Path, tmp_path: Path):
    wt = create_worktree(repo, "scoped")
    secret = tmp_path / "outside.txt"
    secret.write_text("secret", encoding="utf-8")
    try:
        (wt.path / "escape").symlink_to(secret)
    except OSError:
        pytest.skip("symlinks not permitted on this host")

    with pytest.raises(WorktreeEscapeError):
        resolve_within(wt, "escape")


# --- Regressions found by smoking against the real repo ---


def test_worktree_lives_outside_the_repo(repo: Path):
    """Never inside .git/ — git cannot reliably remove a worktree from its own
    gitdir on Windows, which strands the checkout with no way to prune it.
    """
    wt = create_worktree(repo, "placed")

    assert ".git" not in wt.path.parts
    assert repo not in wt.path.parents
    assert wt.path.is_dir()


def test_worktree_root_is_configurable(repo: Path, tmp_path: Path, monkeypatch):
    root = tmp_path / "elsewhere"
    monkeypatch.setenv("STUDIO_WORKTREE_ROOT", str(root))

    wt = create_worktree(repo, "placed")

    assert root in wt.path.parents


def test_capture_diff_survives_non_ascii_content(repo: Path):
    """The real repo is full of emoji; git output must not be decoded as cp1252."""
    (repo / "README.md").write_text("# HyperFocus 🚀♾️\n", encoding="utf-8")
    git(repo, "add", "README.md")
    git(repo, "commit", "-m", "add emoji readme")

    wt = create_worktree(repo, "emoji")
    (wt.path / "README.md").write_text("# HyperFocus 🧠⚡\n", encoding="utf-8")

    diff = capture_diff(wt)

    assert "🧠" in diff
    assert "🚀" in diff


def test_merge_survives_non_ascii_commit_message(repo: Path):
    wt = create_worktree(repo, "emoji-commit")
    (wt.path / "app.py").write_text("print('ok')\n", encoding="utf-8")

    sha = merge_worktree(wt, message="feat: nice one BROski ♾️")

    assert sha == git(repo, "rev-parse", "HEAD")


def test_discard_is_idempotent_when_directory_already_gone(repo: Path):
    """A crashed run can leave the branch behind with no checkout. Clean anyway."""
    import shutil

    wt = create_worktree(repo, "half-dead")
    shutil.rmtree(wt.path)

    discard_worktree(wt)

    assert wt.branch not in git(repo, "branch", "--list", wt.branch)
