"""validate_security() must reject default MinIO credentials unconditionally.

CodeRabbit flagged (PR #453): the check only ran when the MinIO endpoint had
been overridden from its default, so a production/staging deployment that
kept the default endpoint but left minioadmin/minioadmin credentials in place
sailed through validation untouched.
"""
import pytest

from app.core.config import Settings


def _settings(**overrides) -> Settings:
    """Helper: settings."""
    return Settings(ENVIRONMENT="production", JWT_SECRET="a-strong-secret", **overrides)


def test_default_minio_credentials_rejected_even_with_default_endpoint():
    """Test default minio credentials rejected even with default endpoint."""
    settings = _settings(MINIO_ACCESS_KEY="minioadmin", MINIO_SECRET_KEY="minioadmin")
    with pytest.raises(ValueError, match="MinIO credentials"):
        settings.validate_security()


def test_default_access_key_alone_is_rejected():
    """Test default access key alone is rejected."""
    settings = _settings(MINIO_ACCESS_KEY="minioadmin", MINIO_SECRET_KEY="a-real-secret")
    with pytest.raises(ValueError, match="MinIO credentials"):
        settings.validate_security()


def test_non_default_minio_credentials_pass():
    """Test non default minio credentials pass."""
    settings = _settings(MINIO_ACCESS_KEY="real-key", MINIO_SECRET_KEY="real-secret")
    settings.validate_security()
