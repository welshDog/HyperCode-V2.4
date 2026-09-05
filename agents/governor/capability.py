"""PASETO v4.public (Ed25519) capability tokens.

A capability says: this exact mission may perform this exact action against
this exact target until this exact expiry, once. The governor is the only
holder of the signing key; every verifier checks with the public key only.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import pyseto
from pydantic import BaseModel

import keys

ISSUER = "governor"


class Claims(BaseModel):
    """The fields carried inside a signed capability token."""

    iss: str
    sub: str
    mission_id: str
    plan_hash: str
    action: str
    target: Optional[str] = None
    mode: str
    max_attempts: int
    not_before: str
    expires_at: str
    jti: str
    verdict_id: str
    policy_version: str
    approval_id: Optional[str] = None


def mint(
    *,
    sub: str,
    mission_id: str,
    plan_hash: str,
    action: str,
    target: Optional[str],
    mode: str,
    verdict_id: str,
    policy_version: str,
    approval_id: Optional[str] = None,
    ttl_seconds: int = 300,
    max_attempts: int = 1,
    now: Optional[datetime] = None,
) -> tuple[str, Claims]:
    """Sign a new capability token bound to this exact mission/action/target/mode.

    Returns the encoded PASETO token string and the `Claims` it carries.
    `now` is only a test seam; callers should leave it unset.
    """
    now = now or datetime.now(timezone.utc)
    claims = Claims(
        iss=ISSUER,
        sub=sub,
        mission_id=mission_id,
        plan_hash=plan_hash,
        action=action,
        target=target,
        mode=mode,
        max_attempts=max_attempts,
        not_before=now.isoformat(),
        expires_at=(now + timedelta(seconds=ttl_seconds)).isoformat(),
        jti=f"cap_{uuid.uuid4().hex}",
        verdict_id=verdict_id,
        policy_version=policy_version,
        approval_id=approval_id,
    )
    token = pyseto.encode(keys.load_private_key(), payload=claims.model_dump(), serializer=json)
    return token.decode() if isinstance(token, bytes) else token, claims


class VerifyError(Exception):
    """A capability failed verification; `code` names which check failed."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        super().__init__(detail or code)


def verify(
    token: str,
    *,
    expected_sub: str,
    expected_plan_hash: str,
    expected_action: str,
    expected_target: Optional[str],
    expected_mode: str,
    public_key=None,
    now: Optional[datetime] = None,
) -> Claims:
    """Verify a token's signature and bind it to the caller's exact context.

    Checks signature, issuer, subject, plan hash, action/target scope, mode,
    and the not-before/expiry window, in that order. Raises `VerifyError`
    with a specific `code` on the first check that fails; returns the
    decoded `Claims` only if every check passes. Does not consult the
    replay store or kill-switch — callers that need those do so separately.
    """
    now = now or datetime.now(timezone.utc)
    pk = public_key or keys.load_public_key()
    try:
        raw = pyseto.decode(pk, token, deserializer=json).payload
        claims = Claims(**raw)
    except pyseto.exceptions.VerifyError:
        raise VerifyError("bad_signature")
    except Exception:
        raise VerifyError("malformed")

    if claims.iss != ISSUER:
        raise VerifyError("wrong_issuer")
    if claims.sub != expected_sub:
        raise VerifyError("wrong_subject")
    if claims.plan_hash != expected_plan_hash:
        raise VerifyError("plan_hash_mismatch")
    if claims.action != expected_action or (claims.target or None) != (expected_target or None):
        raise VerifyError("out_of_scope")
    if claims.mode != expected_mode:
        raise VerifyError("wrong_mode")
    if now < datetime.fromisoformat(claims.not_before):
        raise VerifyError("not_yet_valid")
    if now >= datetime.fromisoformat(claims.expires_at):
        raise VerifyError("expired")
    return claims
