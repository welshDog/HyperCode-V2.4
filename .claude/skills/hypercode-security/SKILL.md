---
name: hypercode-security
description: Covers HyperCode's internal security model — AES-256-GCM encrypted envelopes, KEYRING key management, anti-replay via Redis nonces, JWT conventions, secret scanning, and threat model. Use when working on agent-to-agent communication security, adding new internal endpoints, rotating keys, or hardening the event bus.
---

# HyperCode Security Skill

## Threat Model Summary

**Do NOT trust the Docker internal network.** Assume any container could be compromised.

Primary threats:
- Fake event injection (malicious "success" / command messages)
- Replay of captured privileged messages
- Payload tampering in Redis pub/sub
- Credential exfiltration from env files

Highest-risk unauthenticated entry points:
- `POST /api/v1/events` in `events_broadcaster.py`
- Plaintext agent pub/sub in `agents/shared/event_bus.py`

---

## Encrypted Envelope Format

All sensitive internal messages MUST use this envelope:

```json
{
  "v": 1,
  "kid": "agent-healer-01",
  "ts": 1712520000,
  "nonce": "base64url(12_bytes)",
  "aad": "POST /api/v1/events",
  "ct": "base64url(aesgcm_ciphertext_plus_tag)"
}
```

### Rules
- `ts` = Unix seconds; reject if `abs(now - ts) > REPLAY_WINDOW_SECONDS` (default 60)
- `nonce` = 96-bit random (12 bytes) for AES-GCM — **NEVER reuse with same key**
- `aad` = binds ciphertext to HTTP method+path (prevents cross-endpoint cut/paste attacks)
- Decrypted plaintext = actual payload (EventPublish, AgentMessage, etc.)

---

## KEYRING Setup

### Per-sender keys (recommended)
Each agent/service gets its own 32-byte key. One compromised agent can't impersonate others.

```bash
# Generate a key
python -c "import os,base64; print(base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip('='))"

# Set in env (Docker secrets in prod, .env for dev only)
HYPERCODE_KEYRING_JSON='{"agent-healer-01":"<b64key>","crew-orchestrator":"<b64key>","hypersync-k1":"<b64key>"}'
HYPERCODE_REPLAY_WINDOW_SECONDS=60
```

### Key rotation
1. Generate new key, add under new `kid` (e.g. `agent-healer-02`)
2. Deploy — system now accepts both old + new `kid`
3. After all agents updated, remove old `kid` from keyring
4. Never reuse `kid` values after retirement

---

## Anti-Replay Implementation

```python
# Redis nonce tracking (one-time use per kid+nonce within window)
replay_key = f"hs:replay:v1:{kid}:{nonce_b64}"
ok = await redis.set(replay_key, str(ts), ex=REPLAY_WINDOW_SECONDS * 2, nx=True)
if not ok:
    raise ValueError("Replay detected")
```

Key points:
- TTL = `REPLAY_WINDOW_SECONDS * 2` — guarantees coverage for the full window
- `NX` flag = only set if not exists (atomic single-use enforcement)
- Bounded memory — keys auto-expire, no manual cleanup needed

---

## Python Crypto Library

Use `cryptography` (already in `backend/requirements.txt`):

```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Encrypt
aesgcm = AESGCM(key_bytes)  # key must be 32 bytes for AES-256
nonce = secrets.token_bytes(12)
ct = aesgcm.encrypt(nonce, plaintext_bytes, aad_bytes)

# Decrypt
pt = aesgcm.decrypt(nonce, ct, aad_bytes)
# Raises cryptography.exceptions.InvalidTag if tampered
```

---

## JWT Conventions

- `JWT_SECRET` default `"dev-secret-key"` in `config.py` — **MUST be overridden in prod**
- JWTs used for user auth only — NOT for agent-to-agent (use AEAD envelope instead)
- JWT does NOT provide anti-replay — don't rely on it for internal messages
- `jsonwebtoken` in Node mission system is **not** JWE-capable

---

## Secret Scanning

- Pre-commit: `detect-secrets` configured in `.pre-commit-config.yaml`
- Baseline: `.secrets.baseline` — update with `detect-secrets scan > .secrets.baseline`
- Semgrep rules: `semgrep.yaml`
- Trivy config: `trivy.yaml` (container + IaC scanning)
- Never commit `.env` — use `docker-compose.secrets.yml` overlay in prod

---

## Key Files

| File | Purpose |
|---|---|
| `backend/app/core/config.py` | All env var definitions incl. JWT_SECRET |
| `backend/app/core/security.py` | JWT creation + verification |
| `backend/app/core/crypto_hypersync.py` | AEAD encrypt/decrypt for HyperSync |
| `agents/shared/event_bus.py` | Redis pub/sub — needs envelope wrapping |
| `backend/app/ws/events_broadcaster.py` | Internal event publish — wrap with envelope |
| `.secrets.baseline` | detect-secrets scan baseline |
| `semgrep.yaml` | Static analysis security rules |
