"""Git worktree sandbox for coder-studio.

An agent never touches the user's working tree. It is given a throwaway git
worktree on its own branch; changes only reach the base branch when a human
merges them. Discarding is always safe.

Every function here is synchronous and shells out to git. Callers running
inside an event loop must wrap them in ``asyncio.to_thread`` — a blocking
subprocess on the loop stalls every other request.
"""

from __future__ import annotations

import os
import re
import secrets
import shutil
import stat
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

WORKTREE_DIRNAME = ".hyperstudio-worktrees"
WORKTREE_ROOT_ENV = "STUDIO_WORKTREE_ROOT"

_SLUG_RE = re.compile(r"[^a-z0-9]+")


class WorktreeError(RuntimeError):
    """A git operation on the sandbox failed."""


class WorktreeEscapeError(WorktreeError):
    """A path resolved outside its worktree. Never let this through."""


@dataclass(frozen=True)
class Worktree:
    repo: Path
    path: Path
    branch: str
    base: str


def _git(cwd: Path, *args: str) -> str:
    # errors="replace" rather than strict: git output carries whatever bytes are
    # in the diff, and a stray byte must never take the service down.
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise WorktreeError(
            f"git {' '.join(args)} failed in {cwd}: {result.stderr.strip()}"
        )
    return result.stdout.strip()


def _rmtree(path: Path, attempts: int = 8) -> None:
    """Delete a tree, tolerating Windows virus-scanner file locks."""

    def _clear_readonly(func, target, _exc):
        os.chmod(target, stat.S_IWRITE)
        func(target)

    for attempt in range(attempts):
        if not path.exists():
            return
        try:
            shutil.rmtree(path, onexc=_clear_readonly)
            return
        except PermissionError:
            time.sleep(0.5 * (attempt + 1))
    if path.exists():
        raise WorktreeError(f"could not remove {path} (locked)")


def worktree_root(repo: Path) -> Path:
    """Where checkouts live. Never inside the repo, and never inside .git."""
    override = os.getenv(WORKTREE_ROOT_ENV)
    if override:
        return Path(override).resolve()
    return (repo.parent / WORKTREE_DIRNAME / repo.name).resolve()


def _slugify(text: str) -> str:
    slug = _SLUG_RE.sub("-", text.lower()).strip("-")
    return (slug or "task")[:40]


def create_worktree(repo: Path, slug: str) -> Worktree:
    """Branch off the current HEAD into an isolated worktree."""
    repo = Path(repo).resolve()
    base = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")

    name = f"{_slugify(slug)}-{secrets.token_hex(3)}"
    branch = f"agent/{name}"

    # Outside the repo entirely. A checkout under .git/ cannot be removed by
    # `git worktree remove` on Windows, which strands thousands of files with
    # no way to prune them.
    path = worktree_root(repo) / name
    path.parent.mkdir(parents=True, exist_ok=True)

    _git(repo, "worktree", "add", "-b", branch, str(path), base)
    return Worktree(repo=repo, path=path.resolve(), branch=branch, base=base)


def capture_diff(worktree: Worktree) -> str:
    """Unified diff of everything the agent changed. Has no side effects.

    Two cases:

    1. Agent only wrote files (normal path): changes are uncommitted.
       ``add -N`` records intent-to-add so new files show up as additions,
       then ``git diff`` shows the unstaged delta.

    2. Agent committed to the branch but the ff-only merge failed (collision
       path): the working tree is clean, but the branch HEAD is ahead of base.
       ``git diff <base>`` shows the full delta between the branch tip and the
       base branch so the human can still review the work before discarding.
    """
    # Check for uncommitted changes first (the normal agent-run path).
    _git(worktree.path, "add", "-A", "-N")
    uncommitted = _git(worktree.path, "diff")
    if uncommitted:
        return uncommitted

    # No uncommitted delta — check whether the branch is ahead of its base
    # (collision path: committed but ff-only merge failed).
    ahead = subprocess.run(
        ["git", "rev-list", "--count", f"{worktree.base}..HEAD"],
        cwd=worktree.path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if ahead.returncode == 0 and ahead.stdout.strip() not in ("", "0"):
        # Branch has commits not yet on base — show the full diff.
        return _git(worktree.path, "diff", worktree.base)

    return uncommitted  # empty string — agent changed nothing


def merge_worktree(worktree: Worktree, message: str) -> str | None:
    """Commit the agent's work and fast-forward it onto the base branch.

    Returns the new commit sha, or None when the agent changed nothing.
    """
    _git(worktree.path, "add", "-A")

    staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=worktree.path,
        capture_output=True,
    )
    if staged.returncode == 0:
        return None

    _git(worktree.path, "commit", "-m", message)
    sha = _git(worktree.path, "rev-parse", "HEAD")

    # ff-only: if the base moved under us, fail loudly rather than
    # inventing a merge commit the human never reviewed.
    _git(worktree.repo, "merge", "--ff-only", worktree.branch)
    return sha


def discard_worktree(worktree: Worktree) -> None:
    """Remove the worktree and its branch. Already-merged commits survive.

    Must succeed from any partial state — a stranded checkout is the worst
    outcome this module can produce, so every step falls back rather than
    raising early.
    """
    if worktree.path.exists():
        try:
            _git(worktree.repo, "worktree", "remove", "--force", str(worktree.path))
        except WorktreeError:
            _rmtree(worktree.path)

    _git(worktree.repo, "worktree", "prune")

    if _git(worktree.repo, "branch", "--list", worktree.branch):
        _git(worktree.repo, "branch", "-D", worktree.branch)


def resolve_within(worktree: Worktree, candidate: str | Path) -> Path:
    """Resolve ``candidate`` against the worktree, refusing anything outside it.

    Resolution follows symlinks, so a link pointing out of the sandbox is
    rejected rather than followed.
    """
    base = worktree.path.resolve()
    target = Path(candidate)
    resolved = (target if target.is_absolute() else base / target).resolve()

    if resolved != base and base not in resolved.parents:
        raise WorktreeEscapeError(f"{candidate!r} resolves outside {base}")
    return resolved
