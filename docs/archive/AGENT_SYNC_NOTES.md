# HyperCode V2.4 — AGENT_SYNC_NOTES

> Last updated: 2026-04-27 | Ecosystem: HyperCode-V2.4 · Hyper-Vibe-Coding-Course · BROskiPets-LLM-dNFT · HyperAgent-SDK

---

## 🏗️ Role in the 4-Repo System

- **Owns** the authoritative V2.4 wallet/economy state
- **Exposes** server endpoints the Course stack calls
- **Source of truth** for spend/unlocks across the ecosystem

---

## 📥 Inbound: Course → V2.4 Token Mirror (Locked Contract)

**Endpoint:** `POST /api/v1/economy/award-from-course`

**Header:**
```
X-Sync-Secret: <COURSE_SYNC_SECRET>
```

**Body:**
```json
{
  "source_id": "uuid-from-supabase-token_transactions.id",
  "discord_id": "string",
  "tokens": 10,
  "reason": "Course reward"
}
```

---

## 📐 Rules

| Rule | Detail |
|---|---|
| **Secret validation** | Constant-time compare vs `COURSE_SYNC_SECRET` |
| **Idempotency** | Dedup on `source_id` — return `409` if already processed (safe no-op) |
| **Identity** | `discord_id` must be linked in V2.4 — return `404` if unknown/unlinked |
| **Success** | Return `200` — include `source_id` in response payload |

---

## 🔑 Shared Vocabulary (All Repos)

| Key | Meaning |
|---|---|
| `source_id` | Idempotency key — always a stable UUID |
| `discord_id` | Cross-repo identity join key |
| `COURSE_SYNC_SECRET` | Auth secret for Course→V2.4 awards (server-only, never browser) |

---

## 🔗 Data Flow

```
Course DB (Supabase)
  └─ token_transactions INSERT
      └─ DB Webhook
          └─ Edge Function: sync-tokens-to-v24
              └─ POST /api/v1/economy/award-from-course  ← THIS REPO
```

---

## ⚠️ Security Stance

- `COURSE_SYNC_SECRET` is **server-only** — never expose in client bundles
- All validation must use constant-time compare (timing-safe)
- Token amounts must be non-negative

---

## 🔗 Related Files

- [`CLAUDE.md`](./CLAUDE.md) — Core brain file
- [`CLAUDE_CONTEXT.md`](./CLAUDE_CONTEXT.md) — Full ecosystem context
- [`RUNBOOK_BLOCKERS.md`](./RUNBOOK_BLOCKERS.md) — Setup steps for this integration
