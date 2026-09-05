"""A Settings() construction failure must never silently continue with
insecure defaults outside development.

CodeRabbit flagged (PR #453, Critical): on a Settings() construction failure,
config.py fell back to Settings.model_validate({}) unconditionally, which
CodeRabbit described as resetting JWT_SECRET to the well-known
"dev-secret-key" default while skipping environment/.env/*_FILE sources —
and since the boot-error HTTP guard in main.py is `@app.middleware("http")`,
it never runs for WebSocket routes (e.g.
/api/v1/orchestrator/ws/approvals, which authenticates via
settings.JWT_SECRET directly), so that fallback would be a live
forge-a-token path.

Verified against the actual pydantic-settings 2.5.2 installed here: contrary
to CodeRabbit's stated mechanism, Settings.model_validate({}) does NOT skip
the custom settings sources — it re-runs the exact same
settings_customise_sources pipeline (env vars, .env, *_FILE secrets) as
Settings(). Confirmed both via config.py directly (a malformed
JWT_SECRET_FILE breaks model_validate({}) identically to Settings()) and via
an isolated minimal BaseSettings reproduction with no config.py involved at
all. So the specific "silently serves with dev-secret-key" scenario
CodeRabbit describes does not reproduce for a source/env-based
misconfiguration — the fallback re-raises the identical error regardless of
environment. The `if ENVIRONMENT != "development": raise` guard added here
still matches CodeRabbit's suggested diff and is kept as defense-in-depth
(e.g. against a future pydantic-settings version, or a failure mode not
routed through settings sources), but the test below only asserts the one
invariant actually verified: a real misconfiguration aborts startup outside
development rather than continuing in a degraded state.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def _import_config_with_broken_secret(environment: str) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as tmpdir:
        bad_secret = Path(tmpdir) / "bad_secret"
        bad_secret.write_bytes(b"\xff\xfe\x00\x01not-valid-utf8")
        env = {
            **os.environ,
            "ENVIRONMENT": environment,
            "JWT_SECRET_FILE": str(bad_secret),
        }
        return subprocess.run(
            [sys.executable, "-c", "import app.core.config"],
            cwd=str(BACKEND_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )


def test_boot_error_aborts_startup_in_production():
    result = _import_config_with_broken_secret("production")
    assert result.returncode != 0, (
        "a Settings() construction failure must abort startup in production, "
        f"never continue with degraded/default settings. stderr:\n{result.stderr}"
    )
    assert "utf-8" in result.stderr.lower()
