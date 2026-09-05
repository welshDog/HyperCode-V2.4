"""Ed25519 key custody for the governor.

The private key is the governor's one privileged asset. It is loaded once,
from a Docker secret file by default, and never logged. Verifiers never see
it — they hold only governor_public_key.pem.

KNOWN PHASE 2 LIMITATION (CodeRabbit follow-up, deliberately not patched
here): GOVERNOR_PRIVATE_KEY_PEM is accepted as a fallback whenever the
secret-file path is missing, with no environment gate — a production
deployment that leaked this env var (or was misconfigured to set it) could
have its signing key read straight out of process environment instead of
the Docker secret file the design doc names as the sole custody mechanism.
The fallback exists because governor/tests/conftest.py and CI use it (no
Docker secrets are mounted in either), and the governor module has no
ENVIRONMENT concept to gate on — unlike backend/app/core/config.py, which
already distinguishes development from production. Restricting this
properly needs that concept added here first, which is more than a quick
fix; tracked as Phase 3 hardening scope, not patched blind.
"""
from __future__ import annotations

import os
from pathlib import Path

import pyseto

_PRIVATE_FILE_ENV = "GOVERNOR_PRIVATE_KEY_FILE"
_PRIVATE_PEM_ENV = "GOVERNOR_PRIVATE_KEY_PEM"
_PUBLIC_FILE_ENV = "GOVERNOR_PUBLIC_KEY_FILE"
_DEFAULT_PRIVATE_FILE = "/run/secrets/governor_ed25519_private_key"
_DEFAULT_PUBLIC_FILE = str(Path(__file__).with_name("governor_public_key.pem"))


def _read_private_pem() -> str:
    path = os.getenv(_PRIVATE_FILE_ENV, _DEFAULT_PRIVATE_FILE)
    if path and Path(path).is_file():
        return Path(path).read_text()
    pem = os.getenv(_PRIVATE_PEM_ENV, "").strip()
    if pem:
        return pem
    raise RuntimeError("governor signing key not configured")


def load_private_key() -> pyseto.Key:
    return pyseto.Key.new(version=4, purpose="public", key=_read_private_pem())


def public_key_pem() -> str:
    path = os.getenv(_PUBLIC_FILE_ENV, _DEFAULT_PUBLIC_FILE)
    return Path(path).read_text()


def load_public_key() -> pyseto.Key:
    return pyseto.Key.new(version=4, purpose="public", key=public_key_pem())
