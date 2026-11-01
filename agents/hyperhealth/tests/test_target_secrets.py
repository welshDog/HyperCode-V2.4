"""Tests for target_secrets - keeps DSN passwords out of stored/returned check targets.

Dependency-free on purpose. Run: pytest agents/hyperhealth/tests/test_target_secrets.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from target_secrets import mask_target, resolve_target  # noqa: E402

# Fake credentials are assembled at runtime so secret scanners do not flag literal user:pw@host URLs.
PW = "fake-" + "pw-value"


def url(scheme: str, userinfo: str, rest: str) -> str:
    return scheme + "://" + userinfo + "@" + rest



def test_masks_password_in_postgres_dsn():
    assert mask_target(url("postgresql", "app:" + PW, "db:5432/hc")) == "postgresql://app:***@db:5432/hc"


def test_masks_driver_suffix_and_redis_urls():
    assert mask_target(url("postgresql+asyncpg", "u:" + PW, "h/db")) == "postgresql+asyncpg://u:***@h/db"
    assert mask_target(url("redis", "default:" + PW, "cache:6379/0")) == "redis://default:***@cache:6379/0"
    assert mask_target(url("redis", ":" + PW, "cache:6379/0")) == "redis://:***@cache:6379/0"


def test_password_containing_at_sign_is_fully_masked():
    out = mask_target(url("postgresql", "app:" + "p@" + "ss", "db/hc"))
    assert "p@ss" not in out and "ss@" not in out.split("***")[0]
    assert out == "postgresql://app:***@db/hc"


def test_masks_inside_an_error_message():
    msg = "could not connect to " + url("postgresql", "app:" + PW, "db:5432/hc") + ": timeout"
    assert PW not in mask_target(msg)


@pytest.mark.parametrize("value", [
    "http://hypercode-core:8000/health",
    "https://user@example.com/path",     # user only, no password
    "redis://cache:6379/0",
    "/",
    "env:DATABASE_URL",
    "http://host/p?x=a@b",               # '@' after the authority is not userinfo
    "",
])
def test_leaves_credential_free_values_alone(value):
    assert mask_target(value) == value


def test_non_strings_pass_through():
    assert mask_target(None) is None


def test_resolve_env_target(monkeypatch):
    dsn = url("postgresql", "u:" + PW, "h/db")
    monkeypatch.setenv("HH_TEST_DSN", dsn)
    assert resolve_target("env:HH_TEST_DSN") == dsn


def test_resolve_plain_target_unchanged():
    assert resolve_target("http://x/health") == "http://x/health"


def test_resolve_missing_env_names_variable_only(monkeypatch):
    monkeypatch.delenv("HH_TEST_MISSING", raising=False)
    with pytest.raises(ValueError) as exc:
        resolve_target("env:HH_TEST_MISSING")
    assert "HH_TEST_MISSING" in str(exc.value)


def test_resolve_empty_env_is_an_error(monkeypatch):
    monkeypatch.setenv("HH_TEST_EMPTY", "")
    with pytest.raises(ValueError):
        resolve_target("env:HH_TEST_EMPTY")
