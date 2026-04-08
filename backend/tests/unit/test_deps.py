import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from jose import jwt

from app.core.config import settings
from app.core import security


def _make_token(sub="1"):
    return jwt.encode({"sub": sub}, settings.JWT_SECRET, algorithm=security.ALGORITHM)


def _mock_db_with_user(active=True, superuser=False):
    user = MagicMock()
    user.is_active = active
    user.is_superuser = superuser
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = user
    return db, user


# ── get_current_user ──────────────────────────────────────────────────────────

def test_get_current_user_valid_token():
    from app.api.deps import get_current_user
    db, user = _mock_db_with_user()
    token = _make_token()
    result = get_current_user(db=db, token=token)
    assert result == user


def test_get_current_user_invalid_token():
    from app.api.deps import get_current_user
    db, _ = _mock_db_with_user()
    with pytest.raises(HTTPException) as exc:
        get_current_user(db=db, token="not.a.real.token")
    assert exc.value.status_code == 403


def test_get_current_user_not_found():
    from app.api.deps import get_current_user
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    token = _make_token()
    with pytest.raises(HTTPException) as exc:
        get_current_user(db=db, token=token)
    assert exc.value.status_code == 404


# ── get_current_active_user ───────────────────────────────────────────────────

def test_get_current_active_user_ok():
    from app.api.deps import get_current_active_user
    _, user = _mock_db_with_user(active=True)
    assert get_current_active_user(current_user=user) == user


def test_get_current_active_user_inactive():
    from app.api.deps import get_current_active_user
    _, user = _mock_db_with_user(active=False)
    with pytest.raises(HTTPException) as exc:
        get_current_active_user(current_user=user)
    assert exc.value.status_code == 400


# ── get_current_active_superuser ─────────────────────────────────────────────

def test_get_current_active_superuser_ok():
    from app.api.deps import get_current_active_superuser
    _, user = _mock_db_with_user(superuser=True)
    assert get_current_active_superuser(current_user=user) == user


def test_get_current_active_superuser_denied():
    from app.api.deps import get_current_active_superuser
    _, user = _mock_db_with_user(superuser=False)
    with pytest.raises(HTTPException) as exc:
        get_current_active_superuser(current_user=user)
    assert exc.value.status_code == 400
