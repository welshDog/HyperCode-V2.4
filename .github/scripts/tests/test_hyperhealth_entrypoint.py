"""Unit tests for HyperHealth's shell-free DHI process entrypoint."""
from __future__ import annotations

import runpy
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ENTRYPOINT = ROOT / "agents" / "hyperhealth" / "entrypoint.py"


class ExecReached(Exception):
    def __init__(self, executable: str, argv: list[str]):
        self.executable = executable
        self.argv = argv


def test_api_runs_migrations_before_replacing_process(monkeypatch):
    calls = []

    def fake_run(argv, check):
        calls.append((argv, check))

    def fake_execvp(executable, argv):
        raise ExecReached(executable, argv)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr("os.execvp", fake_execvp)
    monkeypatch.setattr(sys, "argv", [str(ENTRYPOINT), "api"])

    try:
        runpy.run_path(str(ENTRYPOINT), run_name="__main__")
    except ExecReached as exc:
        assert calls == [(["alembic", "upgrade", "head"], True)]
        assert exc.executable == "uvicorn"
        assert exc.argv == ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090", "--workers", "2"]
    else:
        raise AssertionError("API mode did not exec Uvicorn")


def test_worker_mode_preserves_compose_command_without_migrations(monkeypatch):
    migration_calls = []

    def fake_run(argv, check):
        migration_calls.append(argv)

    def fake_execvp(executable, argv):
        raise ExecReached(executable, argv)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr("os.execvp", fake_execvp)
    monkeypatch.setattr(sys, "argv", [str(ENTRYPOINT), "python", "-m", "worker"])

    try:
        runpy.run_path(str(ENTRYPOINT), run_name="__main__")
    except ExecReached as exc:
        assert migration_calls == []
        assert exc.executable == "python"
        assert exc.argv == ["python", "-m", "worker"]
    else:
        raise AssertionError("worker mode did not exec the Compose command")
