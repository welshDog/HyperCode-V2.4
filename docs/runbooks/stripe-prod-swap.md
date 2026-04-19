# 💳 Runbook — Stripe Production Key Swap + Vercel Env Vars

> **Goal:** flip the live money path from Stripe TEST mode to LIVE mode without downtime.
> **Estimated time:** 5 minutes once you have the prod keys in hand.
> **Last updated:** April 19, 2026

---

## 0. Pre-flight (do these BEFORE swapping)

- [ ] Stripe account is activated for live payments (Stripe dashboard → Settings → Activate account)
- [ ] Bank account verified for payouts
- [ ] Tax forms filed (W-8BEN if you're outside US, otherwise W-9)
- [ ] You have a successful test-mode purchase end-to-end (already done April 18 ✅)

---

## 1. Get the live keys from Stripe

1. Sign in at <https://dashboard.stripe.com> — top-left toggle: **Test mode → Live mode**
2. **Developers → API keys** — copy:
   - `Publishable key` → starts with `pk_live_...`
   - `Secret key` → starts with `sk_live_...` (click "Reveal live key", store immediately, won't show again)
3. **Developers → Webhooks → Add endpoint**:
   - Endpoint URL: `https://api.your-domain.com/api/stripe/webhook`
   - Events to send: `checkout.session.completed`, `invoice.payment_succeeded`, `invoice.payment_failed`, `customer.subscription.updated`, `customer.subscription.deleted`
   - After creating → click endpoint → **Signing secret → Reveal** → copy `whsec_...`

## 2. Re-create the price IDs in LIVE mode

Test-mode prices DO NOT carry over. From Stripe dashboard (Live mode):

**Products → + Add product** — create one product per plan:

| Plan      | Test ID (current)               | Live ID (paste here after create) |
|-----------|---------------------------------|------------------------------------|
| Starter   | `price_1TMPqm2LoEeIEPVE4qwuyu18` | `price_LIVE_...`                   |
| Builder   | `price_1TMPul2LoEeIEPVE2BYeGYtD` | `price_LIVE_...`                   |
| Hyper     | `price_1TMPxd2LoEeIEPVEQVMgK7qI` | `price_LIVE_...`                   |
| Pro Month | `price_1TMQ1X2LoEeIEPVEaL9J1GKp` | `price_LIVE_...`                   |
| Pro Year  | `price_1TMQ4g2LoEeIEPVE9JLBy3g1` | `price_LIVE_...`                   |
| Hyper Month | `price_1TMQ762LoEeIEPVEiaUPgPaA` | `price_LIVE_...`                 |
| Hyper Year  | `price_1TMQ9Y2LoEeIEPVEWhD6F14s` | `price_LIVE_...`                 |

(Match the same prices and currency as test mode.)

## 3. Update `.env` (backend stack)

Replace these 10 lines in `H:\HyperStation zone\HyperCode\HyperCode-V2.4\.env`:

```bash
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_LIVE_...
VITE_STRIPE_PAYMENT_LINK_URL=https://buy.stripe.com/...   # generate fresh link in Live mode
STRIPE_PRICE_STARTER=price_LIVE_...
STRIPE_PRICE_BUILDER=price_LIVE_...
STRIPE_PRICE_HYPER=price_LIVE_...
STRIPE_PRICE_PRO_MONTHLY=price_LIVE_...
STRIPE_PRICE_PRO_YEARLY=price_LIVE_...
STRIPE_PRICE_HYPER_MONTHLY=price_LIVE_...
STRIPE_PRICE_HYPER_YEARLY=price_LIVE_...
```

> ⚠️ **DO NOT commit `.env`.** It is gitignored — keep it that way.
> If you accidentally commit a live secret, rotate it in Stripe **immediately**.

Reload the backend (NO downtime — `up -d --no-deps` recreates only changed):

```bash
docker compose up -d --no-deps hypercode-core celery-worker
```

Verify:

```bash
docker exec hypercode-core sh -c 'echo $STRIPE_SECRET_KEY | cut -c1-8'
# Expected output: sk_live_
```

## 4. Update Vercel env vars (frontend)

Run from the frontend project directory (`HyperCode-Course` or wherever the Next.js / Vite app lives). Requires `vercel` CLI authenticated as the account that owns the project.

```bash
# Remove old test values (if previously set)
vercel env rm VITE_STRIPE_PUBLISHABLE_KEY production
vercel env rm VITE_STRIPE_PAYMENT_LINK_URL production

# Add live values — vercel will prompt for the value
vercel env add VITE_STRIPE_PUBLISHABLE_KEY production
# Paste: pk_live_...

vercel env add VITE_STRIPE_PAYMENT_LINK_URL production
# Paste: https://buy.stripe.com/<live-link>

# Redeploy production with new env
vercel --prod
```

Verify the deploy:

```bash
curl -s https://your-domain.com/_next/static/.../manifest.json   # smoke
# Or: open the live site, view source, search for "pk_live_"
```

## 5. End-to-end smoke test (use a real card — REFUND immediately)

1. Open the live site → /pricing
2. Buy the cheapest plan with your own card (will charge real money)
3. Confirm:
   - [ ] Stripe dashboard (Live mode) → Payments → shows the charge
   - [ ] Backend log: `docker logs hypercode-core --tail 100 | grep stripe` shows `checkout.session.completed` 200
   - [ ] DB record: `docker exec postgres psql -U hypercode_user -d hypercode -c "SELECT * FROM stripe_events ORDER BY created_at DESC LIMIT 1"`
4. **Refund the test charge** in Stripe dashboard → Payments → click → Refund

## 6. Post-swap monitoring (next 24h)

- Watch Grafana → Mission Control → "🚀 HyperCode Tier 3 — Pools & Queues"
- Watch Stripe dashboard → Events for any `*.failed` events
- If anything goes wrong:
  ```bash
  # Quick rollback — revert .env values + redeploy frontend
  git checkout HEAD -- .env   # only works if you DID commit, which you shouldn't
  # Better: keep a copy of the prior .env at .env.test-backup before swapping
  ```

## 7. Update `CLAUDE.md` after success

Add to `## 🏆 Achievements Unlocked`:

```markdown
- ✅ **Stripe LIVE mode** — pk_live + sk_live + webhook signing live. First real payment received <date>. (April 2026)
```

Update the "Known Issues" table — flip `VITE_STRIPE_PAYMENT_LINK_URL empty` to ✅ DONE.

---

## 🆘 If the webhook doesn't fire

1. Stripe dashboard → Developers → Webhooks → click your endpoint → **Recent deliveries**
2. Look for the failed POST → check the response code
3. Common causes:
   - Webhook URL not publicly reachable (firewall/cloudflare blocking)
   - `STRIPE_WEBHOOK_SECRET` mismatch — copied the wrong env's secret
   - Backend rate limiter blocking webhook (Sacred Rule: webhook is rate-limit EXEMPT — verify in `backend/app/main.py`)

## 🆘 If frontend still shows test mode

- Vercel cache: trigger a clean rebuild → `vercel --prod --force`
- Browser cache: hard reload (Ctrl+Shift+R)
- Check the deployed bundle for `pk_test_` strings — if present, env wasn't applied
