"""Tests for secret_env.read_secret - the API_KEY / API_KEY_FILE loader.

Dependency-free on purpose (does not import main.py, which needs a DB URL and FastAPI).
Run: pytest agents/hyperhealth/tests/test_secret_env.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from secret_env import read_secret  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("DEMO_KEY", raising=False)
    monkeypatch.delenv("DEMO_KEY_FILE", raising=False)


def test_reads_file_and_strips_trailing_newline(tmp_path, monkeypatch):
    f = tmp_path / "secret.txt"
    f.write_text("from-file-value\n", encoding="utf-8")
    monkeypatch.setenv("DEMO_KEY_FILE", str(f))
    assert read_secret("DEMO_KEY") == "from-file-value"


def test_file_wins_over_plain_env(tmp_path, monkeypatch):
    f = tmp_path / "secret.txt"
    f.write_text("from-file", encoding="utf-8")
    monkeypatch.setenv("DEMO_KEY_FILE", str(f))
    monkeypatch.setenv("DEMO_KEY", "from-env")
    assert read_secret("DEMO_KEY") == "from-file"


def test_falls_back_to_env_when_no_file_var(monkeypatch):
    monkeypatch.setenv("DEMO_KEY", "from-env")
    assert read_secret("DEMO_KEY") == "from-env"


def test_falls_back_to_env_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_KEY_FILE", str(tmp_path / "does-not-exist"))
    monkeypatch.setenv("DEMO_KEY", "from-env")
    assert read_secret("DEMO_KEY") == "from-env"


def test_falls_back_to_env_when_file_empty(tmp_path, monkeypatch):
    f = tmp_path / "empty.txt"
    f.write_text("  \n", encoding="utf-8")
    monkeypatch.setenv("DEMO_KEY_FILE", str(f))
    monkeypatch.setenv("DEMO_KEY", "from-env")
    assert read_secret("DEMO_KEY") == "from-env"


def test_empty_when_nothing_configured():
    assert read_secret("DEMO_KEY") == ""


def test_blank_file_var_is_ignored(monkeypatch):
    monkeypatch.setenv("DEMO_KEY_FILE", "   ")
    monkeypatch.setenv("DEMO_KEY", "from-env")
    assert read_secret("DEMO_KEY") == "from-env"


def test_unreadable_path_is_a_directory(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_KEY_FILE", str(tmp_path))  # a directory -> OSError on read
    monkeypatch.setenv("DEMO_KEY", "from-env")
    assert read_secret("DEMO_KEY") == "from-env"
