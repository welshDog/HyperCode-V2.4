"""Unit tests for JWT creation and the decode rules the API applies.

The backend has no ``verify_token`` helper: ``app.api.deps`` decodes tokens
inline with jose. ``_decode`` below applies the same parameters, so these tests
cover the same acceptance rules (secret, algorithm, expiry, issuer, audience).
"""
from datetime import timedelta

import pytest
from jose import JWTError, jwt


def _security():
    from app.core import security

    return security


def _decode(token):
    from app.core.config import settings

    return jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[_security().ALGORITHM],
        audience=settings.JWT_AUDIENCE,
        issuer=settings.JWT_ISSUER,
    )


def test_valid_token_roundtrip():
    token = _security().create_access_token("user123")
    assert _decode(token)["sub"] == "user123"


def test_subject_is_stringified():
    token = _security().create_access_token(42)
    assert _decode(token)["sub"] == "42"


def test_expired_token_raises():
    token = _security().create_access_token(
        "user123", expires_delta=timedelta(seconds=-1)
    )
    with pytest.raises(JWTError):
        _decode(token)


def test_malformed_token_raises():
    with pytest.raises(JWTError):
        _decode("totally.fake.token")


def test_tampered_token_raises():
    token = _security().create_access_token("user123")
    # Flip the last character of the signature.
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(JWTError):
        _decode(tampered)


def test_wrong_secret_raises():
    token = _security().create_access_token("user123")
    with pytest.raises(JWTError):
        jwt.decode(
            token,
            "not-the-signing-secret",
            algorithms=[_security().ALGORITHM],
            options={"verify_aud": False, "verify_iss": False},
        )
