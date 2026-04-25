from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
from pathlib import Path
from typing import Any


def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )
    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    return proc.returncode, stdout if stdout else stderr


def get_changed_files(workspace_path: Path) -> list[str]:
    code, out = _run(["git", "status", "--short"], cwd=workspace_path)
    if code != 0:
        return []
    lines = [line.rstrip() for line in out.splitlines() if line.strip()]
    return lines


def get_last_commit(workspace_path: Path) -> str:
    code, out = _run(["git", "log", "--oneline", "-1"], cwd=workspace_path)
    return out if code == 0 and out else "No commits found"


def get_last_test_result(workspace_path: Path) -> str | None:
    candidates = [
        workspace_path / "backend" / ".pytest_cache" / "v" / "cache" / "lastfailed",
        workspace_path / ".pytest_cache" / "v" / "cache" / "lastfailed",
        workspace_path / "reports" / "junit-python.xml",
        workspace_path / "coverage.xml",
        workspace_path / "backend" / "coverage.xml",
    ]

    existing = [p for p in candidates if p.exists() and p.is_file()]
    if not existing:
        return None

    newest = max(existing, key=lambda p: p.stat().st_mtime)
    if newest.name == "lastfailed":
        try:
            payload: Any = json.loads(newest.read_text(encoding="utf-8"))
            if isinstance(payload, dict) and payload:
                failing = ", ".join(sorted(payload.keys())[:5])
                suffix = "…" if len(payload) > 5 else ""
                return f"Failing tests detected: {failing}{suffix}"
            return "Last pytest run: all passing"
        except Exception:
            return "Last pytest run: unknown"

    if newest.name.endswith(".xml"):
        return f"Recent test report found: {newest.relative_to(workspace_path).as_posix()}"

    return f"Recent coverage found: {newest.relative_to(workspace_path).as_posix()}"


def get_suggested_next_action(workspace_path: Path) -> str:
    whats_done_path = workspace_path / "WHATS_DONE.md"
    if not whats_done_path.exists():
        return "Open WHATS_DONE.md and pick the first item in NEXT UP"

    lines = whats_done_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        if line.strip().startswith("##") and "NEXT UP" in line:
            header_idx = i
            break
    if header_idx is None:
        return "Open WHATS_DONE.md and pick the first item in NEXT UP"

    for raw in lines[header_idx + 1 :]:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("##"):
            break
        if line[0].isdigit() and "." in line[:4]:
            return line.split(".", 1)[1].strip()
        if line.startswith("- "):
            return line[2:].strip()

    return "Open WHATS_DONE.md and pick the first item in NEXT UP"


def write_session_md(workspace_path: Path, output_path: Path | None = None) -> Path:
    resolved_workspace = workspace_path.resolve()
    out = (output_path or (resolved_workspace / "SESSION.md")).resolve()

    generated_at = dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M UTC")
    last_commit = get_last_commit(resolved_workspace)
    changed_files = get_changed_files(resolved_workspace)
    next_action = get_suggested_next_action(resolved_workspace)
    test_result = get_last_test_result(resolved_workspace) or "No recent test run found"

    changed_block = "All clean ✅" if not changed_files else "\n".join(changed_files)

    content = "\n".join(
        [
            "# 👋 Welcome Back — Session Snapshot",
            f"> Generated: {generated_at}",
            "",
            "## 📝 Last commit",
            last_commit,
            "",
            "## 📁 Changed files (not committed)",
            changed_block,
            "",
            "## 🎯 Your next action",
            next_action,
            "",
            "## 🧪 Last test run",
            test_result,
            "",
        ]
    )

    out.write_text(content, encoding="utf-8")
    return out


def workspace_from_env() -> Path:
    value = os.getenv("WORKSPACE_PATH") or os.getenv("WORKSPACE") or "."
    return Path(value)
