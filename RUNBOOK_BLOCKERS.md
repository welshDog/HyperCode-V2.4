# 🔴 Blockers Runbook — B1 / B2 / B3

> Stuff I couldn't do for you because it needs dashboards, a browser, or a real card.
> Work top → bottom. ~20 min total.

---

## ✅ Already done (this session)

- **B2 V2.4 side**: `COURSE_SYNC_SECRET` set in `.env` ✅
  (+ `SHOP_SYNC_SECRET` set for when Phase 3 lands) ✅
- **B4**: Celery `task_acks_late=True` verified live ✅
- **B5**: endpoint verified — wrong secret → 401, missing header → 422, unknown discord_id → 404 ✅
- **Q3**: `VITE_STRIPE_PAYMENT_LINK_URL` set in `frontend/.env.local` (Course repo) + V2.4 .env

---

## B1 — Register Supabase DB webhook (5 min)

**Goal:** every `token_transactions` INSERT fires `sync-tokens-to-v24` Edge Function.

1. Go to https://supabase.com/dashboard/project/yhtmuibgdnxhbgboajhc/database/hooks
2. Click **Create a new hook**
3. Fill in:
   - **Name**: `sync_tokens_to_v24`
   - **Table**: `public.token_transactions`
   - **Events**: ✅ Insert (only)
   - **Type**: **Supabase Edge Functions**
   - **Edge Function**: `sync-tokens-to-v24`
   - **HTTP Headers**: (none — the function reads the secret from its own env vars)
   - **HTTP Params**: (none)
4. Click **Create hook**

Verify: Insert a test row and confirm it fires.
```sql
-- In Supabase SQL editor:
INSERT INTO token_transactions (user_id, amount, reason)
VALUES ('<your-test-user-uuid>', 10, 'B1 webhook test');
-- Then Dashboard → Edge Functions → sync-tokens-to-v24 → Logs — should see an invocation.
```

---

## B2 — Set `COURSE_SYNC_SECRET` in Supabase (3 min)

**Goal:** Supabase Edge Function holds the same secret V2.4 expects in the `X-Sync-Secret` header.

1. Go to https://supabase.com/dashboard/project/yhtmuibgdnxhbgboajhc/settings/functions
2. Under **Secrets**, click **Add new secret** (or Edit if it exists)
3. Name: `COURSE_SYNC_SECRET`
   Value: `<use the same value as V2.4 COURSE_SYNC_SECRET>`
4. Also set (for when Phase 3 lands):
   `SHOP_SYNC_SECRET` = `<use the same value as V2.4 SHOP_SYNC_SECRET>`
5. Save.

> Note: the mission list calls it `COURSE_WEBHOOK_SECRET` but the V2.4 code reads
> `settings.COURSE_SYNC_SECRET` (see `backend/app/api/v1/endpoints/economy.py:59`).
> Canonical name is **`COURSE_SYNC_SECRET`** — use that both sides.

After saving, the Edge Function will pick it up on next invocation.

---

## B3 — E2E Stripe Checkout test (~10 min)

**Goal:** real money path proven end-to-end.

### Terminal 1 — webhook forwarder
```bash
stripe listen --forward-to localhost:8000/api/stripe/webhook
```
Copy the `whsec_...` signing secret it prints.
Check V2.4 `.env`: `STRIPE_WEBHOOK_SECRET=<value printed by stripe listen>`.
If `stripe listen` prints a different secret, update `.env` to match, then:
```bash
cd "H:/HyperStation zone/HyperCode/HyperCode-V2.4"
docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d --no-deps hypercode-core
```

### Terminal 2 — create a checkout
```bash
curl -X POST http://localhost:8000/api/stripe/checkout \
  -H "Content-Type: application/json" \
  -d '{"plan":"starter"}'
```
Grab the `checkout_url` from the response.

### Browser
1. Open the `checkout_url`
2. Card: `4242 4242 4242 4242`, any future expiry, any CVC, any postcode
3. Complete payment

### Verify
- Terminal 1 (stripe listen): should print `checkout.session.completed` + `payment_intent.succeeded` → `[200 OK]`
- DB:
  ```bash
  docker exec postgres psql -U postgres -d hypercode -c "SELECT stripe_payment_intent_id, amount, plan FROM payments ORDER BY created_at DESC LIMIT 1;"
  ```
- BROski$ balance increased by 200 (starter grant):
  ```bash
  docker exec postgres psql -U postgres -d hypercode -c "SELECT email, broski_tokens FROM users ORDER BY updated_at DESC LIMIT 3;"
  ```

---

## Q8 — Publish `@w3lshdog/hyper-agent@0.1.7` (5 min)

```bash
cd H:/HyperAgent-SDK
npm login            # if not logged in
npm publish --access public
```

Smoke test:
```bash
npx @w3lshdog/hyper-agent validate --help
```

---

## Q3 part 2 — Vercel env vars (5 min)

Same value needs to land in Vercel for production builds:
1. https://vercel.com/lyndzwills/hyper-vibe-coding-course/settings/environment-variables
2. Add `VITE_STRIPE_PAYMENT_LINK_URL` = `https://buy.stripe.com/test_5kQ00c3nd9tB6mCfI48EM00`
3. Scope: Production + Preview + Development (or just Production to start)
4. Redeploy the latest deployment (⋯ → Redeploy)

---

## 🟢 When B1–B3 are green

- B1 ✅ + B2 ✅ → Token sync auto-fires end-to-end (ship a student lesson → coins in V2.4 within 30s)
- B3 ✅ → full money path proven; you can tell the world Stripe is live
- Q8 ✅ → SDK is installable via `npx`

Then Phase 1 is **complete**. UI tweaking is unlocked. 🎨

---
*Written by Claude, April 18 2026. Everything auto-doable is done.*
