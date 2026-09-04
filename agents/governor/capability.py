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
