---
name: hypercode-supabase
description: Supabase integration patterns for the HyperCode ecosystem — Edge Functions, RLS policies, DB webhooks, migrations, and the Supabase ↔ V2.4 sync bridge. Use when working on token sync, Supabase Edge Functions, database webhooks, RLS rules, or any Supabase-side work in the Course repo. Also covers the critical manual setup steps.
---

# HyperCode Supabase Skill

## Two Separate Supabase Projects (NEVER mix these)

| Project | Used by | Schema authority |
|---------|---------|-----------------|
| Course Supabase | Hyper-Vibe-Coding-Course | Supabase migrations |
| V2.4 Postgres | HyperCode V2.4 | Alembic migrations |

**Sacred Rule: Supabase schema NEVER merges with V2.4 Postgres.**

---

## ⚠️ CRITICAL MANUAL STEPS (must be done by Lyndz)

### Step 1 — Register DB Webhook (Phase 2 Token Sync)
```
Supabase Dashboard → Database → Webhooks → Create webhook
  Name:     token-sync-trigger
  Table:    token_transactions
  Events:   INSERT
  Method:   POST
  URL:      https://{project-ref}.supabase.co/functions/v1/sync-tokens-to-v24
  Headers:  Authorization: Bearer {SUPABASE_SERVICE_ROLE_KEY}
```

### Step 2 — Set COURSE_WEBHOOK_SECRET
```
Supabase Dashboard → Edge Functions → sync-tokens-to-v24 → Secrets
  Add: COURSE_WEBHOOK_SECRET = {same value as in V2.4 .env}

V2.4 .env:
  COURSE_WEBHOOK_SECRET=some-long-random-secret-here
```

Both must match exactly or the token sync will reject all webhook calls.

---

## Edge Functions (all in supabase/functions/)

| Function | Trigger | Purpose |
|----------|---------|---------|
| `stripe-webhook` | Stripe webhook | Payment processing → award tokens |
| `shop-purchase` | HTTP POST | Shop item purchase → deduct tokens |
| `sync-tokens-to-v24` | DB webhook on token_transactions | Sync BROski$ to V2.4 |
| `course-profile` | HTTP GET | Return user's cross-system profile by Discord ID |

## Deploy Edge Functions

```bash
# From hyper-vibe-coding-course root:
supabase functions deploy stripe-webhook
supabase functions deploy shop-purchase
supabase functions deploy sync-tokens-to-v24
supabase functions deploy course-profile

# Test a function
curl https://{project-ref}.supabase.co/functions/v1/course-profile \
  -H "Authorization: Bearer {ANON_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"discord_id": "test123"}'
```

## Database Schema (Course Supabase)

### courses table
```sql
id           text PRIMARY KEY
title        text NOT NULL
slug         text UNIQUE NOT NULL
description  text
price_pence  integer   -- GBP pence (£29 = 2900)
currency     text DEFAULT 'gbp'
is_active    boolean DEFAULT true
created_at   timestamptz DEFAULT now()
```

### users table (key columns)
```sql
id              uuid PRIMARY KEY  -- Supabase auth user ID
discord_id      varchar(30) UNIQUE  -- links to V2.4
broski_tokens   integer DEFAULT 0
loyalty_tier    text DEFAULT 'free'
```

### token_transactions table
```sql
id          uuid DEFAULT gen_random_uuid() PRIMARY KEY
user_id     uuid REFERENCES users(id)
amount      integer NOT NULL  -- positive=credit, negative=debit
reason      text
source_id   text UNIQUE  -- idempotency key
created_at  timestamptz DEFAULT now()
```

## RLS Rules (NEVER change security_invoker)

```sql
-- CORRECT — security_invoker enforces RLS for the querying user
CREATE VIEW public.user_loyalty_tier
  WITH (security_invoker = on) AS
  SELECT ...;

-- WRONG — bypasses RLS
CREATE VIEW public.user_loyalty_tier
  SECURITY DEFINER AS
  SELECT ...;
```

## Stripe Webhook Setup

```
Webhook name:    vibe-hook  (keep this one — has delivery history)
Endpoint:        https://{project}.supabase.co/functions/v1/stripe-webhook
Events:          checkout.session.completed, charge.refunded
Secret:          STRIPE_WEBHOOK_SECRET in Supabase env vars
                 (must match vibe-hook signing secret from Stripe dashboard)

Note: brilliant-triumph webhook = duplicate, safe to delete
```

## Migration Naming Convention

```
20260418000029_your_migration_name.sql
  └── timestamp: YYYYMMDDHHMMSS
  └── sequence:  000029 (next after 000028)
```

## Testing Edge Functions Locally

```bash
supabase start  # starts local Supabase
supabase functions serve --env-file .env.local

# In another terminal:
curl http://localhost:54321/functions/v1/sync-tokens-to-v24 \
  -H "Content-Type: application/json" \
  -H "x-sync-secret: your-secret-here" \
  -d '{"discord_id": "test", "delta": 100, "reason": "test", "source_id": "test-001"}'
```

## Token Sync Smoke Test (V2.4 side)

```bash
curl -X POST http://localhost:8000/api/v1/economy/award-from-course \
  -H "Content-Type: application/json" \
  -H "X-Sync-Secret: $(grep COURSE_WEBHOOK_SECRET .env | cut -d= -f2)" \
  -d '{"discord_id": "test_user", "delta": 50, "reason": "smoke test", "source_id": "smoke-001"}'

# Expected: {"ok": true, "new_balance": 50}
# Check idempotency — run again with same source_id → balance stays at 50
```
