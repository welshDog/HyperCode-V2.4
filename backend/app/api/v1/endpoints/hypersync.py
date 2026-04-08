from __future__ import annotations

import json
import re
from typing import Any, Optional

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app.api import deps
from app.core.config import settings
from app.core.hypersync import (
    _sha256_hex,
    build_state_bytes,
    compress_bytes,
    decrypt_bytes,
    decompress_bytes,
    encrypt_bytes,
    new_handoff_id,
    new_resume_token,
)
from app.core.storage import get_storage


router = APIRouter()

IDEMPOTENCY_KEY_RE = re.compile(r"^[a-zA-Z0-9_-]{8,128}$")

RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 10


class HyperFileRef(BaseModel):
    path: str = Field(min_length=1, max_length=4096)
    line_start: Optional[int] = Field(default=None, ge=1)
    line_end: Optional[int] = Field(default=None, ge=1)


class HyperMessage(BaseModel):
    role: str = Field(min_length=1, max_length=32)
    content: str = Field(min_length=0, max_length=20000)
    timestamp: int


class HyperSyncState(BaseModel):
    client_id: str = Field(min_length=6, max_length=128)
    messages: list[HyperMessage] = Field(default_factory=list, max_length=2000)
    context_variables: dict[str, Any] = Field(default_factory=dict)
    file_references: list[HyperFileRef] = Field(default_factory=list, max_length=500)
    user_preferences: dict[str, Any] = Field(default_factory=dict)
    session_meta: dict[str, Any] = Field(default_factory=dict)


class HyperSyncHandoffResponse(BaseModel):
    handoff_id: str
    resume_token: str
    expires_in_seconds: int
    pt_sha256: str
    mode: str


class HyperSyncRedeemRequest(BaseModel):
    resume_token: str = Field(min_length=20, max_length=512)
    client_id: str = Field(min_length=6, max_length=128)


class HyperSyncRedeemResponse(BaseModel):
    handoff_id: str
    pt_sha256: str
    state: dict[str, Any]


async def _redis() -> aioredis.Redis:
    return aioredis.from_url(settings.HYPERCODE_REDIS_URL, decode_responses=True)


def _require_master_key() -> str:
    key = (settings.HYPERSYNC_MASTER_KEY or "").strip()
    if not key:
        raise HTTPException(status_code=503, detail="HyperSync not configured")
    return key


def _validate_idempotency_key(value: str) -> None:
    if not IDEMPOTENCY_KEY_RE.match(value):
        raise HTTPException(status_code=422, detail="Invalid idempotency key")


async def _enforce_rate_limit(r: aioredis.Redis, request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    # Privacy-first: never persist raw IP addresses in Redis keys.
    salt = (settings.HYPERSYNC_MASTER_KEY or "hypersync").strip()
    ip_bucket = _sha256_hex(f"{salt}:{ip}")[:16]
    key = f"hypersync:ratelimit:{ip_bucket}"
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, RATE_LIMIT_WINDOW_SECONDS)
    if count > RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")


@router.post("/handoff", response_model=HyperSyncHandoffResponse)
async def hypersync_handoff(
    request: Request,
    state: HyperSyncState,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    x_idempotency_key: Optional[str] = Header(default=None, alias="X-Idempotency-Key"),
    current_user=Depends(deps.get_optional_current_user),
) -> Any:
    master_key = _require_master_key()
    user_id = getattr(current_user, "id", None)
    ttl = int(settings.HYPERSYNC_TOKEN_TTL_SECONDS)
    session_ttl = int(settings.HYPERSYNC_SESSION_TTL_SECONDS)

    idem = (idempotency_key or x_idempotency_key or "").strip() or None

    r = await _redis()
    try:
        await _enforce_rate_limit(r, request)

        if idem:
            _validate_idempotency_key(idem)
            idem_key = f"hypersync:idem:{user_id or 'anon'}:{state.client_id}:{idem}"
            existing = await r.get(idem_key)
            if existing:
                data = json.loads(existing)
                return HyperSyncHandoffResponse.model_validate(data)

        handoff_id = new_handoff_id()
        resume_token = new_resume_token()
        aad = f"handoff:{handoff_id}:{user_id or 'anon'}:{state.client_id}"

        payload = {
            "v": 1,
            "handoff_id": handoff_id,
            "user_id": user_id,
            "client_id": state.client_id,
            "messages": [m.model_dump() for m in state.messages],
            "context_variables": state.context_variables,
            "file_references": [f.model_dump() for f in state.file_references],
            "user_preferences": state.user_preferences,
            "session_meta": state.session_meta,
        }

        raw, pt_sha256 = build_state_bytes(payload)
        compressed = compress_bytes(raw)
        envelope = encrypt_bytes(master_key, compressed, aad=aad)

        envelope_record = {"envelope": envelope, "aad": aad, "pt_sha256": pt_sha256}
        envelope_json = json.dumps(envelope_record, separators=(",", ":"))

        mode = "inline"
        payload_value: dict[str, Any] = {"mode": "inline", **envelope_record}

        if len(envelope_json.encode("utf-8")) > int(settings.HYPERSYNC_INLINE_MAX_BYTES):
            storage = get_storage()
            object_key = storage.upload_file(
                envelope_json,
                filename=f"hypersync/{handoff_id}.json",
                metadata={"client_id": state.client_id, "pt_sha256": pt_sha256},
            )
            if object_key:
                mode = "backchannel"
                payload_value = {"mode": "backchannel", "object_key": object_key, "aad": aad, "pt_sha256": pt_sha256}

        payload_key = f"hypersync:payload:{handoff_id}"
        token_key = f"hypersync:token:{resume_token}"

        await r.set(payload_key, json.dumps(payload_value), ex=session_ttl)
        await r.set(
            token_key,
            json.dumps({"handoff_id": handoff_id, "user_id": user_id, "client_id": state.client_id}),
            ex=ttl,
            nx=True,
        )

        response = HyperSyncHandoffResponse(
            handoff_id=handoff_id,
            resume_token=resume_token,
            expires_in_seconds=ttl,
            pt_sha256=pt_sha256,
            mode=mode,
        )

        if idem:
            idem_key = f"hypersync:idem:{user_id or 'anon'}:{state.client_id}:{idem}"
            await r.set(idem_key, response.model_dump_json(), ex=min(ttl, 900), nx=True)

        return response
    finally:
        await r.aclose()


@router.post("/redeem", response_model=HyperSyncRedeemResponse)
async def hypersync_redeem(
    req: HyperSyncRedeemRequest,
    current_user=Depends(deps.get_optional_current_user),
) -> Any:
    master_key = _require_master_key()
    user_id = getattr(current_user, "id", None)

    r = await _redis()
    try:
        redeemed_key = f"hypersync:redeemed:{req.resume_token}"
        cached = await r.get(redeemed_key)
        if cached:
            return HyperSyncRedeemResponse.model_validate_json(cached)

        token_key = f"hypersync:token:{req.resume_token}"
        token_data_raw = await r.get(token_key)
        if not token_data_raw:
            raise HTTPException(status_code=410, detail="Resume token expired or already used")

        token_data = json.loads(token_data_raw)
        if token_data.get("client_id") != req.client_id:
            raise HTTPException(status_code=403, detail="Invalid client")
        if token_data.get("user_id") is not None and token_data.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Invalid user")

        handoff_id = str(token_data["handoff_id"])
        payload_key = f"hypersync:payload:{handoff_id}"
        payload_raw = await r.get(payload_key)
        if not payload_raw:
            raise HTTPException(status_code=404, detail="Payload not found")

        payload = json.loads(payload_raw)
        mode = payload.get("mode", "inline")

        if mode == "backchannel" and payload.get("object_key"):
            storage = get_storage()
            remote = storage.get_file_content(str(payload["object_key"]))
            if not remote:
                raise HTTPException(status_code=404, detail="Backchannel payload not found")
            remote_payload = json.loads(remote)
            envelope = remote_payload["envelope"]
            aad = remote_payload["aad"]
            expected_pt_sha256 = remote_payload["pt_sha256"]
        else:
            envelope = payload["envelope"]
            aad = payload["aad"]
            expected_pt_sha256 = payload["pt_sha256"]

        compressed = decrypt_bytes(master_key, envelope=envelope, aad=aad)
        raw = decompress_bytes(compressed)
        if _sha256_hex(raw) != expected_pt_sha256:
            raise HTTPException(status_code=409, detail="Integrity verification failed")

        state = json.loads(raw.decode("utf-8"))
        response = HyperSyncRedeemResponse(
            handoff_id=handoff_id,
            pt_sha256=expected_pt_sha256,
            state=state,
        )

        await r.set(redeemed_key, response.model_dump_json(), ex=60, nx=True)
        await r.delete(token_key)
        return response
    finally:
        await r.aclose()

