# 🔴 STRIPE E2E SMOKE TEST RUNBOOK — 2026-06-06

> P0 Blocker. Run this. Prove money works. Then launch.
> Estimated time: 30 mins

---

## PRE-CHECKS (2 mins)

```powershell
# 1. Confirm hypercode-core is running
docker ps | grep hypercode-core
# Expected: Up X hours, healthy

# 2. Confirm Stripe CLI is installed
stripe --version
# If missing: https://stripe.com/docs/stripe-cli

# 3. Confirm webhook secret is set in Supabase
# Go to: https://supabase.com/dashboard/project/yhtmuibgdnxhbgboajhc/settings/functions
# Check env var: STRIPE_WEBHOOK_SECRET = whsec_...
```

---

## STEP 1 — Start Stripe Listener (Terminal 1)

```powershell
stripe listen --forward-to http://localhost:8000/webhook/stripe
```

> Copy the `whsec_...` secret it prints.
> Paste it into your `.env` as `STRIPE_WEBHOOK_SECRET=whsec_...`
> Sacred Rule: webhook is ALWAYS rate-limit exempt ✅

---

## STEP 2 — Trigger Test Event (Terminal 2)

```powershell
# Basic checkout complete
stripe trigger checkout.session.completed

# Also test subscription
stripe trigger customer.subscription.created

# Also test invoice
stripe trigger invoice.payment_succeeded
```

---

## STEP 3 — Check Webhook Received

```powershell
# Watch hypercode-core logs
docker logs hypercode-core --tail=50 --follow

# Expected log lines:
# INFO: Stripe webhook received: checkout.session.completed
# INFO: Payment recorded. user_id=xxx amount=xxx
# INFO: BROski$ awarded: xxx tokens
```

---

## STEP 4 — Check Database (Supabase)

```sql
-- In Supabase SQL editor:
-- https://supabase.com/dashboard/project/yhtmuibgdnxhbgboajhc/sql

-- Check payment recorded
SELECT * FROM payments 
ORDER BY created_at DESC 
LIMIT 5;

-- Check tokens awarded
SELECT * FROM token_transactions 
ORDER BY created_at DESC 
LIMIT 5;

-- Check user balance updated
SELECT id, email, broski_tokens 
FROM users 
ORDER BY updated_at DESC 
LIMIT 5;
```

---

## STEP 5 — Test Idempotency (CRITICAL)

```powershell
# Re-send the SAME event — should NOT create duplicate rows
stripe trigger checkout.session.completed

# Then re-run Step 4 SQL
# payments table should still have same count (no duplicate)
# token_transactions should NOT have a second row for same event
```

---

## STEP 6 — Test Real Card Flow (Optional but Gold)

```
1. Go to your course pricing page (Vercel)
2. Click buy — use test card: 4242 4242 4242 4242
   Expiry: any future date | CVC: any 3 digits
3. Complete checkout
4. Check redirect to /payment-success
5. Re-run Step 4 SQL — confirm real row created
```

---

## ✅ PASS CRITERIA

| Check | Expected | Pass? |
|---|---|---|
| Webhook received | 200 OK in logs | ⬜ |
| `payments` row created | 1 new row | ⬜ |
| `token_transactions` row | tokens awarded | ⬜ |
| `users.broski_tokens` updated | balance increased | ⬜ |
| Idempotency | no duplicate on re-send | ⬜ |
| Real card flow | /payment-success loads | ⬜ |

---

## ❌ IF IT FAILS

### Webhook returns 400
- Check `STRIPE_WEBHOOK_SECRET` matches what `stripe listen` printed
- Check rate limiting — webhook MUST be exempt (Sacred Rule)

### No DB row created
- Check `docker logs hypercode-core` for Python errors
- Check Supabase edge function logs for `stripe-webhook`

### Duplicate rows on re-send
- Idempotency key check failing — check `stripe_event_id` unique constraint

---

## 📝 RECORD YOUR RESULTS HERE

```
Date tested: 2026-06-06
Tested by: @welshDog
Result: PASS / FAIL
Webhook status: 
DB rows created: 
Tokens awarded: 
Idempotency: 
Notes: 
```

---

> 🔥 Once this passes — you're revenue-proven. Ship it Bro! BROski♾️
