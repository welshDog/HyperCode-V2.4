"""Offline capability verification. fleet-controller holds ONLY the governor
public key — it can check a token but never mint one. Phase 2: the result is
recorded, not enforced (a missing/invalid capability still returns a preview);
Phase 4 makes it blocking for LIVE.

No cross-agent imports: this module does not import anything from
agents/governor/ — it re-implements the tiny bit of verify logic it needs
against its own vendored copy of the public key.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pyseto

_PUBLIC_FILE_ENV = "GOVERNOR_PUBLIC_KEY_FILE"
_DEFAULT_PUB = str(Path(__file__).with_name("governor_public_key.pem"))


def _public_key_path() -> str:
    """Path to the vendored governor public key PEM (env-overridable)."""
    return os.getenv(_PUBLIC_FILE_ENV, _DEFAULT_PUB)


def _public_key() -> pyseto.Key:
    """Load the vendored governor public key for offline verification."""
    return pyseto.Key.new(version=4, purpose="public", key=Path(_public_key_path()).read_text())


def verify_or_none(
    token: Optional[str], *, plan_hash: str, action: str, target: Optional[str], mode: str
) -> tuple[bool, str]:
    """Verify a capability token against this exact context, offline.

    Returns `(True, "ok")` only if the signature, issuer, subject, plan
    hash, action/target scope, mode, and time window all check out;
    otherwise `(False, <reason>)`. Never raises — a missing or malformed
    token is just another failure reason, not an exception.
    """
    if not token:
        return False, "no capability presented"
    try:
        claims = pyseto.decode(_public_key(), token, deserializer=json).payload
    except Exception:
        return False, "bad signature or malformed capability"
    if claims.get("iss") != "governor":
        return False, "wrong issuer"
    if claims.get("sub") != "fleet-controller":
        return False, "wrong subject"
    if claims.get("plan_hash") != plan_hash:
        return False, "plan_hash mismatch"
    if claims.get("action") != action or (claims.get("target") or None) != (target or None):
        return False, "action/target out of scope"
    if claims.get("mode") != mode:
        return False, "mode mismatch"
    now = datetime.now(timezone.utc)
    try:
        if now < datetime.fromisoformat(claims["not_before"]):
            return False, "not yet valid"
        if now >= datetime.fromisoformat(claims["expires_at"]):
            return False, "expired"
    except Exception:
        return False, "malformed time window"
    return True, "ok"
