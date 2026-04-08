"""Unit tests for JWT security functions."""
import pytest
from datetime import timedelta
from unittest.mock import patch


def _get_security_module():
    try:
        from backend.app.core import security
        return security
    except ImportError:
        from app.core import security
        return security


def test_valid_token_roundtrip():
    security = _get_security_module()
    token = security.create_access_token({"sub": "user123"})
    payload = security.verify_token(token)
    assert payload["sub"] == "user123"


def test_expired_token_raises():
    security = _get_security_module()
    token = security.create_access_token(
        {"sub": "user123"}, expires_delta=timedelta(seconds=-1)
    )
    with pytest.raises(Exception):
        security.verify_token(token)


def test_invalid_signature_raises():
    security = _get_security_module()
    with pytest.raises(Exception):
        security.verify_token("totally.fake.token")


def test_tampered_token_raises():
    security = _get_security_module()
    token = security.create_access_token({"sub": "user123"})
    # Flip one character in the signature portion
    tampered = token[:-3] + ("X" if token[-1] != "X" else "Y")
    with pytest.raises(Exception):
        security.verify_token(tampered)
