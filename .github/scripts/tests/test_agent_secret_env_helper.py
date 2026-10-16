"""Tests for agents/shared/secret_env.read_secret (the canonical helper vendored into the agents).

Run: python -m pytest .github/scripts/tests/test_agent_secret_env_helper.py
"""
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "agents" / "shared"))
from secret_env import read_secret  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in ("DEMO_KEY", "DEMO_KEY_FILE"):
        monkeypatch.delenv(k, raising=False)


def _file(tmp_path, text, raw=None):
    f = tmp_path / "secret.txt"
    if raw is not None:
        f.write_bytes(raw)
    else:
        f.write_text(text, encoding="utf-8")
    return str(f)


def test_identical_to_plain_getenv_when_no_file_var(monkeypatch):
    """The safety property: until a *_FILE var is set, behaviour == os.getenv."""
    assert read_secret("DEMO_KEY") == ""
    monkeypatch.setenv("DEMO_KEY", "from-env")
    assert read_secret("DEMO_KEY") == os.getenv("DEMO_KEY") == "from-env"


def test_file_wins_over_env_and_is_stripped(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_KEY_FILE", _file(tmp_path, "from-file\r\n"))
    monkeypatch.setenv("DEMO_KEY", "from-env")
    assert read_secret("DEMO_KEY") == "from-file"


def test_bom_is_stripped(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_KEY_FILE", _file(tmp_path, None, raw=b"\xef\xbb\xbfwith-bom\n"))
    assert read_secret("DEMO_KEY") == "with-bom"


@pytest.mark.parametrize("content", ["", "   \n"])
def test_empty_file_falls_back_to_env(tmp_path, monkeypatch, content):
    monkeypatch.setenv("DEMO_KEY_FILE", _file(tmp_path, content))
    monkeypatch.setenv("DEMO_KEY", "from-env")
    assert read_secret("DEMO_KEY") == "from-env"


def test_missing_file_and_directory_fall_back_to_env(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_KEY", "from-env")
    monkeypatch.setenv("DEMO_KEY_FILE", str(tmp_path / "nope"))
    assert read_secret("DEMO_KEY") == "from-env"
    monkeypatch.setenv("DEMO_KEY_FILE", str(tmp_path))  # a directory -> OSError
    assert read_secret("DEMO_KEY") == "from-env"


def test_undecodable_file_fails_closed_to_env(tmp_path, monkeypatch):
    monkeypatch.setenv("DEMO_KEY_FILE", _file(tmp_path, None, raw=b"\xff\xfe\x00bad\xff"))
    monkeypatch.setenv("DEMO_KEY", "from-env")
    assert read_secret("DEMO_KEY") == "from-env"


def test_blank_file_var_is_ignored_and_default_applies(monkeypatch):
    monkeypatch.setenv("DEMO_KEY_FILE", "   ")
    assert read_secret("DEMO_KEY") == ""
    assert read_secret("DEMO_KEY", "fallback") == "fallback"


def test_is_re_read_on_every_call(tmp_path, monkeypatch):
    """Rotation: a rewritten secret file is picked up without restarting the agent."""
    f = _file(tmp_path, "old")
    monkeypatch.setenv("DEMO_KEY_FILE", f)
    assert read_secret("DEMO_KEY") == "old"
    Path(f).write_text("new", encoding="utf-8")
    assert read_secret("DEMO_KEY") == "new"
