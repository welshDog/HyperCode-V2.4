# HyperSync Patterns

## Inline Flow (small payload < 32KB)

```
client → POST /hypersync/handoff
  → encrypt state (AES-256-GCM)
  → mint token (Redis NX EX 300)
  → return { token, sessionId, mode: "inline" }

client → POST /hypersync/redeem { token }
  → GETDEL token (single-use consume)
  → decrypt state
  → return { state, conversationHistory }
```

## Back-Channel Flow (large payload > 32KB)

```
client → POST /hypersync/sessions        → { sessionId, mode: "backchannel", uploadConfig }
client → PUT  /hypersync/sessions/{id}/chunks/{seq}  → upload encrypted chunks to MinIO
client → POST /hypersync/sessions/{id}/commit        → finalise + publish pointer event
recipient → GET /hypersync/inbox/{id}                → receive pointer
recipient → POST /hypersync/sessions/{id}/redeem     → get download token
recipient → GET  /hypersync/sessions/{id}/download   → stream encrypted bytes
```

## Retry Pattern

- Require `X-Idempotency-Key` on all mutating requests
- Chunk re-send: same `seq` + matching `chunkSha256` = accepted (idempotent)
- Different `chunkSha256` on same `seq` = 409 Conflict
- `ack(status="failed")` triggers automatic resend from sender
