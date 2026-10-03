"""HyperCrew Day 3 — redaction of agent output before it is stored or shown."""

import pytest

from app.crew.redaction import REDACTED, is_sensitive_key, redact_text, redact_value


@pytest.mark.parametrize("secret", [
    "sk-abcdefghijklmnopqrstuvwxyz123456",
    "sk-ant-api03-abcdefghijklmnopqrstuvwx",
    "ghp_abcdefghijklmnopqrstuvwxyz0123",
    "github_pat_abcdefghijklmnopqrstuvwxyz",
    "AKIAABCDEFGHIJKLMNOP",
    "xoxb-1234567890-abcdefghij",
    "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkw.abcdefghijklmnop",
    "Bearer abcdefghijklmnopqrstuvwxyz012345",
])
def test_known_secret_shapes_are_redacted(secret):
    out = redact_text(f"before {secret} after")
    assert secret not in out and REDACTED in out and out.startswith("before") and out.endswith("after")


def test_private_key_block_is_redacted():
    key = "-----BEGIN RSA PRIVATE KEY-----\nMIIEabc\ndef\n-----END RSA PRIVATE KEY-----"
    assert "MIIEabc" not in redact_text(f"x\n{key}\ny")


def test_unterminated_private_key_is_still_redacted():
    assert "MIIEabc" not in redact_text("-----BEGIN PRIVATE KEY-----\nMIIEabc")


def test_repo_scrub_text_still_applies():
    out = redact_text("connect postgres://user:pw@host/db password=hunter2")
    assert "hunter2" not in out and "user:pw" not in out


def test_clean_text_is_untouched():
    assert redact_text("add a health endpoint to the API") == "add a health endpoint to the API"


def test_redaction_is_idempotent():
    once = redact_text("key sk-abcdefghijklmnopqrstuvwxyz123456 end")
    assert redact_text(once) == once


@pytest.mark.parametrize("key", ["api_key", "API_KEY", "Authorization", "x_token", "db_password", "client_secret", "Cookie"])
def test_sensitive_keys(key):
    assert is_sensitive_key(key)


@pytest.mark.parametrize("key", ["goal", "summary", "status", "agent"])
def test_ordinary_keys_are_not_sensitive(key):
    assert not is_sensitive_key(key)


def test_values_under_sensitive_keys_are_replaced_whole():
    out = redact_value({"summary": "ok", "api_key": "anything", "nested": {"password": 123, "n": 1}})
    assert out == {"summary": "ok", "api_key": REDACTED, "nested": {"password": REDACTED, "n": 1}}


def test_redaction_walks_lists_and_nested_dicts_without_mutating_input():
    original = {"items": [{"t": "sk-abcdefghijklmnopqrstuvwxyz123456"}, "ghp_abcdefghijklmnopqrstuvwxyz0123", 5]}
    out = redact_value(original)
    assert out == {"items": [{"t": REDACTED}, REDACTED, 5]}
    assert "sk-abc" in original["items"][0]["t"]


def test_non_string_scalars_pass_through():
    assert redact_value(None) is None and redact_value(3) == 3 and redact_value(True) is True
