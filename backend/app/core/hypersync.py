import base64
import hashlib
import json
import secrets
import time
import uuid
import zlib
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(raw: str) -> bytes:
    pad = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode((raw + pad).encode("ascii"))


def _sha256_hex(raw: bytes | str) -> str:
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def build_state_bytes(state: dict[str, Any]) -> tuple[bytes, str]:
    raw = json.dumps(state, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return raw, _sha256_hex(raw)


def compress_bytes(raw: bytes) -> bytes:
    return zlib.compress(raw, level=9)


def decompress_bytes(raw: bytes) -> bytes:
    return zlib.decompress(raw)


def encrypt_bytes(master_key_b64: str, plaintext: bytes, aad: str) -> dict[str, Any]:
    try:
        key = _b64url_decode(master_key_b64)
    except Exception as exc:
        raise ValueError("Invalid hypersync master key encoding") from exc
    if len(key) != 32:
        raise ValueError("Invalid AES key length")

    aesgcm = AESGCM(key)
    nonce = secrets.token_bytes(12)
    ct = aesgcm.encrypt(nonce, plaintext, aad.encode("utf-8"))
    return {
        "v": 1,
        "alg": "aes-256-gcm",
        "kid": "hypersync-k1",
        "nonce": _b64url_encode(nonce),
        "aad": aad,
        "ct": _b64url_encode(ct),
        "ct_sha256": _sha256_hex(ct),
        "ts": int(time.time()),
    }


def decrypt_bytes(master_key_b64: str, envelope: dict[str, Any], aad: str) -> bytes:
    if not isinstance(envelope, dict):
        raise ValueError("Invalid envelope structure")
    if not all(k in envelope for k in ("nonce", "ct", "ct_sha256")):
        raise ValueError("Invalid envelope structure")
    if int(envelope.get("v", 0)) != 1:
        raise ValueError("Unsupported hypersync envelope version")
    if envelope.get("alg") != "aes-256-gcm":
        raise ValueError("Unsupported hypersync envelope algorithm")

    try:
        key = _b64url_decode(master_key_b64)
    except Exception as exc:
        raise ValueError("Invalid hypersync master key encoding") from exc
    if len(key) != 32:
        raise ValueError("Invalid AES key length")

    try:
        nonce = _b64url_decode(str(envelope["nonce"]))
        ct = _b64url_decode(str(envelope["ct"]))
    except Exception as exc:
        raise ValueError("Invalid envelope structure") from exc
    if _sha256_hex(ct) != str(envelope.get("ct_sha256")):
        raise ValueError("Ciphertext integrity check failed")

    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ct, aad.encode("utf-8"))


def new_handoff_id() -> str:
    return f"hs_{uuid.uuid4().hex}"


def new_resume_token() -> str:
    return secrets.token_urlsafe(32)

