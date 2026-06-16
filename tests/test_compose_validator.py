"""Tests for scripts/compose_validator.py

Run with:
    pytest tests/test_compose_validator.py -v
"""
import textwrap
from pathlib import Path

import pytest

# Allow importing from scripts/
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from compose_validator import validate


def _write(tmp_path, content):
    """Write dedented YAML to a temp file and return its Path."""
    f = tmp_path / "docker-compose.test.yml"
    f.write_text(textwrap.dedent(content), encoding="utf-8")
    return f


# ---------------------------------------------------------------------------
# 1. Clean file — no errors, no warnings
# ---------------------------------------------------------------------------
def test_clean_file_passes(tmp_path):
    f = _write(tmp_path, """\
        services:
          api:
            image: ghcr.io/welshdog/api:latest
            ports:
              - "8000:8000"
    """)
    errors, warnings = validate(f)
    assert errors == []
    assert warnings == []


# ---------------------------------------------------------------------------
# 2. docker.io reference — must error
# ---------------------------------------------------------------------------
def test_dockerio_image_blocked(tmp_path):
    f = _write(tmp_path, """\
        services:
          redis:
            image: docker.io/library/redis:7
    """)
    errors, warnings = validate(f)
    assert any("docker.io" in e for e in errors), f"Expected docker.io error, got: {errors}"


# ---------------------------------------------------------------------------
# 3. index.docker.io reference — must also error
# ---------------------------------------------------------------------------
def test_index_dockerio_blocked(tmp_path):
    f = _write(tmp_path, """\
        services:
          app:
            image: index.docker.io/library/nginx:alpine
    """)
    errors, _ = validate(f)
    assert any("docker.io" in e for e in errors)


# ---------------------------------------------------------------------------
# 4. Forbidden import pattern — must error
# ---------------------------------------------------------------------------
def test_forbidden_import_blocked(tmp_path):
    f = _write(tmp_path, """\
        services:
          worker:
            command: python -c "from backend.app.core import settings"
    """)
    errors, _ = validate(f)
    assert any("backend.app" in e for e in errors), f"Expected backend.app error, got: {errors}"


# ---------------------------------------------------------------------------
# 5. healthcheck 127.0.0.1 — must WARN (not error)
# ---------------------------------------------------------------------------
def test_healthcheck_127_warns(tmp_path):
    f = _write(tmp_path, """\
        services:
          api:
            image: ghcr.io/welshdog/api:latest
            healthcheck:
              test: ["CMD", "curl", "-f", "http://127.0.0.1:8000/health"]
              interval: 30s
    """)
    errors, warnings = validate(f)
    assert errors == []
    assert any("127.0.0.1" in w for w in warnings), f"Expected 127.0.0.1 warning, got: {warnings}"


# ---------------------------------------------------------------------------
# 6. CORS_ALLOW_ORIGINS with 127.0.0.1 — must NOT warn (the bug we fixed!)
# ---------------------------------------------------------------------------
def test_cors_origins_not_flagged(tmp_path):
    """Regression test for d1f71fe — CORS env var must NOT trigger healthcheck warning."""
    f = _write(tmp_path, """\
        services:
          api:
            image: ghcr.io/welshdog/api:latest
            healthcheck:
              test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
              interval: 30s
            environment:
              CORS_ALLOW_ORIGINS: "http://127.0.0.1:3000,http://localhost:3000"
    """)
    errors, warnings = validate(f)
    assert errors == []
    assert warnings == [], f"False positive warnings: {warnings}"


# ---------------------------------------------------------------------------
# 7. Multi-service — healthcheck state resets between services
# ---------------------------------------------------------------------------
def test_healthcheck_state_resets_between_services(tmp_path):
    """Healthcheck block must not bleed from service A into service B's env vars."""
    f = _write(tmp_path, """\
        services:
          redis:
            image: ghcr.io/welshdog/redis:7
            healthcheck:
              test: ["CMD", "redis-cli", "ping"]
              interval: 10s
          api:
            image: ghcr.io/welshdog/api:latest
            environment:
              DATABASE_URL: "postgresql://user:pass@127.0.0.1:5432/db"
    """)
    errors, warnings = validate(f)
    assert errors == []
    assert warnings == [], f"State bled across services: {warnings}"


# ---------------------------------------------------------------------------
# 8. File not found — must return error gracefully
# ---------------------------------------------------------------------------
def test_file_not_found(tmp_path):
    missing = tmp_path / "does-not-exist.yml"
    errors, warnings = validate(missing)
    assert any("not found" in e for e in errors)
    assert warnings == []
