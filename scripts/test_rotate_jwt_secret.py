"""Tests for the pure helpers in rotate_jwt_secret.py (fake data only; never touches real secrets)."""
import base64, json, sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from rotate_jwt_secret import drop_env_line, get_env_value, jwt_claims, replace_env_line, sha8  # noqa: E402

FAKE = "A=1\nHYPERCODE_JWT_SECRET=oldoldold\nJWT_SECRET=other\nDASHBOARD_SERVICE_JWT=eyJ.fake.tok\nZ=9\n"


def test_replace_only_the_named_line():
    out = replace_env_line(FAKE, "HYPERCODE_JWT_SECRET", "NEW")
    assert "HYPERCODE_JWT_SECRET=NEW\n" in out and "JWT_SECRET=other\n" in out and "oldoldold" not in out


def test_replace_does_not_touch_a_key_that_merely_ends_the_same():
    # JWT_SECRET must not match HYPERCODE_JWT_SECRET (anchored at line start)
    out = replace_env_line(FAKE, "JWT_SECRET", "X")
    assert "HYPERCODE_JWT_SECRET=oldoldold" in out and "\nJWT_SECRET=X\n" in out


def test_replace_keeps_crlf_endings():
    out = replace_env_line(FAKE.replace("\n", "\r\n"), "HYPERCODE_JWT_SECRET", "NEW")
    assert "HYPERCODE_JWT_SECRET=NEW\r\n" in out and "\n" not in out.replace("\r\n", "")


@pytest.mark.parametrize("text", ["A=1\n", "K=1\nK=2\n"])
def test_replace_refuses_missing_or_duplicate(text):
    with pytest.raises(ValueError):
        replace_env_line(text, "K" if "K=" in text else "HYPERCODE_JWT_SECRET", "v")


def test_drop_removes_exactly_that_line_and_is_a_noop_when_absent():
    assert drop_env_line(FAKE, "DASHBOARD_SERVICE_JWT") == "A=1\nHYPERCODE_JWT_SECRET=oldoldold\nJWT_SECRET=other\nZ=9\n"
    assert drop_env_line("A=1\n", "DASHBOARD_SERVICE_JWT") == "A=1\n"
    assert drop_env_line(FAKE.replace("\n", "\r\n"), "DASHBOARD_SERVICE_JWT").count("\r\n") == 4


def test_get_env_value_strips_quotes_and_cr():
    assert get_env_value('K="v"\r\n', "K") == "v" and get_env_value("A=1\n", "K") is None


def test_jwt_claims_decodes_without_verifying():
    b = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()
    tok = f"{b({'alg': 'HS256'})}.{b({'sub': '9', 'exp': 1})}.sig"
    assert jwt_claims(tok) == {"sub": "9", "exp": 1}


def test_sha8_is_a_short_stable_prefix_that_does_not_contain_the_value():
    assert sha8("abc") == sha8("abc") and len(sha8("abc")) == 8 and "abc" not in sha8("abc")
