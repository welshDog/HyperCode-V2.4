# Phase 2 — Token Sync Bridge

> Course (Supabase) → HyperCode V2.4 (FastAPI/Docker)
> When a student earns BROski$ in the Course, V2.4 mirrors the award automatically.

---

## How it works

```
Course DB INSERT on token_transactions
        │
        ▼ (Supabase DB Webhook)
sync-tokens-to-v24 Edge Function
        │
        │  POST /api/v1/economy/award-from-course
        │  Header: X-Sync-Secret: <shared secret>
        ▼
HyperCode V2.4 FastAPI
        │
        ├── UNIQUE check on course_sync_events.source_id  (idempotency)
        ├── Lookup User by discord_id
        ├── broski_service.award_coins()
        └── INSERT course_sync_events row
```

---

## Environment variables

### V2.4 (`.env` / Docker secrets)

```env
COURSE_SYNC_SECRET=<32-byte hex string — see generation below>
```

### Supabase Edge Function secrets

```bash
supabase secrets set COURSE_SYNC_SECRET=<same value>
supabase secrets set V24_API_URL=https://<your-public-v24-domain>
```

> `V24_API_URL` must be publicly reachable. For local dev use an ngrok tunnel:
> `ngrok http 8000` → copy the `https://...ngrok.io` URL.

---

## Generating the shared secret

```bash
openssl rand -hex 32
```

Copy the output. Set it identically in both places above. Never commit it.

---

## Deploy the Edge Function

```bash
cd "H:\the hyper vibe coding hub"
supabase functions deploy sync-tokens-to-v24 --no-verify-jwt
```

`--no-verify-jwt` is required because this function is called by a DB webhook,
not by a logged-in user — there is no Bearer token in the request.

---

## Register the Supabase Database Webhook

1. Go to **Supabase Dashboard → Database → Webhooks**
2. Click **Create a new hook**
3. Fill in:

| Field | Value |
|---|---|
| Name | `sync-tokens-to-v24` |
| Table | `token_transactions` |
| Events | `INSERT` |
| Type | Supabase Edge Function |
| Edge Function | `sync-tokens-to-v24` |

4. Save.

From this point on, every positive `token_transactions` INSERT fires the edge function.

---

## Test with a manual curl command

Replace `<...>` with your values before running:

```bash
curl -X POST https://<your-public-v24-url>/api/v1/economy/award-from-course \
  -H "Content-Type: application/json" \
  -H "X-Sync-Secret: <COURSE_SYNC_SECRET>" \
  -d '{
    "source_id": "test-uuid-manual-001",
    "discord_id": "<a real discord_id from your users table>",
    "tokens": 50,
    "reason": "Manual test award"
  }'
```

Expected response on success:

```json
{
  "awarded": true,
  "coins_balance": 50,
  "xp_balance": 0,
  "level": 1,
  "source_id": "test-uuid-manual-001"
}
```

Send the same request again — you should get a `409` (idempotency guard working correctly).

---

## Idempotency guarantee

Every award carries a `source_id` — this is the `token_transactions.id` UUID from Supabase.

V2.4 stores it in `course_sync_events` with a `UNIQUE` constraint.

- **App layer:** checks for an existing row before awarding. Returns 409 if found.
- **DB layer:** `UNIQUE` constraint is the final guard against race conditions.

This means Supabase can safely retry a failed webhook delivery without double-awarding coins.

---

## Skipped events

The edge function silently skips (returns `ok: true, skipped: true`) for:

| Condition | Reason |
|---|---|
| `amount <= 0` | Refunds / deductions — not mirrored to V2.4 |
| `discord_id` is null | Student has not linked Discord — no V2.4 user to award |
| V2.4 returns 409 | Already processed — safe no-op |

A `404` from V2.4 means the discord_id is not linked to any V2.4 account yet.
The student should run `/link-discord` in the Discord bot.

---

## V2.4 Backend — what's already live

| Component | Location | Status |
|---|---|---|
| `CourseSyncEvent` ORM model | `backend/app/models/broski.py` | ✅ Live |
| Alembic migration | `backend/alembic/versions/004_add_course_sync_events.py` | ✅ Live |
| `POST /api/v1/economy/award-from-course` | `backend/app/api/v1/endpoints/economy.py` | ✅ Live |
| Router registered | `backend/app/api/api.py` | ✅ Live |
| Model imported at startup | `backend/app/main.py` (via `import app.models.broski`) | ✅ Live |
| `COURSE_SYNC_SECRET` setting | `backend/app/core/config.py` | ✅ Live |

---

## Course Supabase — what's already live

| Component | Location | Status |
|---|---|---|
| `sync-tokens-to-v24` Edge Function | `supabase/functions/sync-tokens-to-v24/index.ts` | ✅ Live |

**Remaining step:** Register the DB Webhook in Supabase Dashboard (see above).
