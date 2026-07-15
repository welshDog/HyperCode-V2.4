---
name: stripe-webhook-handler
description: HyperCode V2.4 Stripe Checkout + webhook flow — Phase 10F (API), 10G (DB writes), 10I (e2e), 10K (price IDs locked). Routes, prices, webhook events, signature verification, rate-limit exemption. Use when the user says "stripe", "checkout", "webhook failing", "subscription event", "price ID", "10F/10G/10I", or hits any payment-related issue.
---

# stripe-webhook-handler

The complete Stripe surface for V2.4 — checkout sessions, webhook receiver, DB writes, idempotency. **Phase 10F–10K live since April 14–15, 2026.**

## Endpoints (LIVE)

| Method | Path | What |
|---|---|---|
| POST | `/api/stripe/checkout` | Creates a Checkout Session, returns redirect URL |
| POST | `/api/stripe/webhook` | Receives Stripe events (rate-limit EXEMPT) |
| GET | `/api/stripe/prices` | Returns the locked price catalogue |

Source: `backend/app/api/stripe.py` + service layer.

## Locked Prices (LOCKED April 14, 2026 — never re-quote without checking)

### BROski Token Packs (one-time)

| Pack | Price | Tokens | Stripe Product |
|---|---|---|---|
| Starter | £5 GBP | 200 | BROski Starter Pack |
| Builder | £15 GBP | 800 | BROski Builder Pack |
| Hyper | £35 GBP | 2500 | BROski Hyper Pack |

### Course Subscriptions (recurring)

| Tier | Monthly | Yearly | Stripe Product |
|---|---|---|---|
| Pro | £9/mo | £90/yr | Hyper Vibe Pro Course |
| Hyper | £29/mo | £290/yr | Hyper Elite |

## Required `.env` Keys

```env
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_PRICE_STARTER=price_xxx
STRIPE_PRICE_BUILDER=price_xxx
STRIPE_PRICE_HYPER=price_xxx
STRIPE_PRICE_PRO_MONTHLY=price_xxx
STRIPE_PRICE_PRO_YEARLY=price_xxx
STRIPE_PRICE_HYPER_MONTHLY=price_xxx
STRIPE_PRICE_HYPER_YEARLY=price_xxx
```

**Local-dev gotcha:** missing `STRIPE_WEBHOOK_SECRET` = signature check skipped. Production MUST have it.

## Checkout Flow

```
Browser
  → POST /api/stripe/checkout { price_id: "starter", user_id: "broski_xyz" }
  ← { url: "https://checkout.stripe.com/..." }
  → window.location.href = url
  → User pays on Stripe-hosted page
  → Stripe POSTs to /api/stripe/webhook
  → V2.4 verifies signature + writes to DB
  → User redirected back to success URL
```

`price_id` arg accepts these slugs (mapped to `STRIPE_PRICE_*` env vars):
`starter | builder | hyper | pro_monthly | pro_yearly | hyper_monthly | hyper_yearly`

## Webhook Events (Phase 10G — all handled)

| Event | Action | Where |
|---|---|---|
| `checkout.session.completed` | Subscription activated, write to `subscriptions` table | webhook handler |
| `customer.subscription.deleted` | Mark subscription cancelled | webhook handler |
| `invoice.payment_failed` | Log payment failure warning | webhook handler |
| `customer.subscription.updated` | Status change logged | webhook handler |

## Hard Rules

- **`/api/stripe/webhook` is rate-limit EXEMPT** — NEVER wrap it with rate limiting middleware. Stripe retries with backoff and rate-limiting will cause silent event drops.
- **Webhook signature MUST be verified in production** — using `STRIPE_WEBHOOK_SECRET`. Skipping = anyone can forge events.
- **Idempotency** — every webhook handler must use `event.id` as the idempotency key. Stripe replays events, our DB writes must be safe.
- **Never accept `price_id` from the client untrusted** — map slug → env var on the server.
- **Webhook is async** — don't block the response. Return 2xx fast, do work in a background task or queue.

## Local Testing (Stripe CLI — Phase 10I)

```powershell
# Forward webhook events to local V2.4
stripe listen --forward-to localhost:8000/api/stripe/webhook

# In another shell, run a test checkout
curl -X POST http://localhost:8000/api/stripe/checkout `
  -H "Content-Type: application/json" `
  -d '{"price_id": "starter", "user_id": "broski_test"}'

# Or trigger a test webhook event directly
stripe trigger checkout.session.completed
```

The `stripe listen` command prints the webhook signing secret to use locally — copy it into `STRIPE_WEBHOOK_SECRET` for the dev session.

## Tests

```powershell
cd "H:\HyperStation zone\HyperCode\HyperCode-V2.4"
pytest backend/tests/test_stripe.py -v
```

Covers checkout creation, webhook signature verification, event handlers, idempotency.

## Frontend Pattern (where the Course calls in)

```ts
// frontend/src/lib/payments.ts (Course repo, not V2.4)
import { createCheckoutSession } from '../lib/payments'

const url = await createCheckoutSession(priceKey, user.id)
window.location.href = url
```

API target: `VITE_HYPERCODE_API_URL` env var (default `http://localhost:8000`).

## Common Failures

| Symptom | Cause | Fix |
|---|---|---|
| 400 from `/api/stripe/checkout` | Unknown `price_id` slug | Use one of the 7 documented slugs |
| Webhook signature verification fails (locally) | `STRIPE_WEBHOOK_SECRET` not the one from `stripe listen` | Re-copy from `stripe listen` output |
| Webhook signature verification fails (prod) | Wrong secret in `.env` (test vs live mismatch) | Pull from Stripe Dashboard → Developers → Webhooks → Signing secret |
| Subscription not appearing in DB | Event handler crashed silently | Check container logs (`docker compose logs hypercode-core`) |
| Duplicate DB rows from one purchase | Idempotency key not used | Use `event.id` as the key |
| `429 Too Many Requests` from Stripe | Webhook handler is slow + rate-limited (we never rate-limit FROM us) | Speed up handler, return 2xx fast |
| Customer billed but no access granted | Webhook delivered but handler rejected it | Stripe Dashboard → Webhooks → Recent deliveries → see the response body |

## Companion Skills

- `phase-10-tracker` — Phase 10F–10K context
- `docker-stack-ops` — debugging the `hypercode-core` container
- `otlp-tempo-tracing` — tracing a checkout request end-to-end
