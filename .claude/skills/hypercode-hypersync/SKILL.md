---
name: hypercode-hypersync
description: Manages HyperSync encrypted session handoff — serializes, compresses, and encrypts chat/session state so it can be resumed in a fresh context. Covers threshold detection, AES-256-GCM envelopes, single-use resume tokens, Redis storage, optional MinIO backchannel, and frontend resume flow.
---

# HyperCode HyperSync

HyperSync transfers session state across context window boundaries so a user can continue seamlessly.

## When to use

- Context window / chat approaching size limit (Dashboard Cognitive Uplink uses a char threshold)
- User wants to continue a session in a new tab or fresh instance
- Debugging resume failures (410 expired, 403 wrong client, 409 integrity failure, 429 rate limit)

## Backend endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/hypersync/handoff` | Encrypt + store state, return single-use `resume_token` |
| POST | `/api/v1/hypersync/redeem` | Validate token, decrypt + verify state, consume token |

## Core behavior

- **Compression:** zlib
- **Encryption:** AES-256-GCM (AEAD)
- **Token:** single-use resume token stored in Redis and deleted on successful redeem
- **Retry window:** server caches the first redeem for a short period to allow client retry
- **Rate limit:** `/handoff` is limited per IP
- **Backchannel (optional):** oversized encrypted blobs can be stored in MinIO and only a pointer is kept in Redis

## Key files

| File | Purpose |
|------|---------|
| `backend/app/core/hypersync.py` | Crypto primitives (compress/encrypt/decrypt/sha256) |
| `backend/app/api/v1/endpoints/hypersync.py` | FastAPI router (`/handoff`, `/redeem`) |
| `backend/app/core/config.py` | `HYPERSYNC_*` settings |
| `backend/app/api/api.py` | Router registration under `/api/v1/hypersync` |
| `agents/dashboard/lib/api.ts` | Frontend helpers `hypersyncHandoff`, `hypersyncRedeem` |
| `agents/dashboard/components/CognitiveUplink.tsx` | UI threshold detection + “Sync complete—continue here” |

