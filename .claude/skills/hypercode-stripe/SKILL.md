---
name: hypercode-stripe
description: Stripe payment integration for HyperCode V2.4 — checkout sessions, webhook verification, plan management, and E2E testing. Use when working on Stripe checkout, webhook handling, payment success flows, or running local Stripe tests.
---

# HyperCode Stripe Skill

## Sacred Rules (NEVER break these)
- `/api/stripe/webhook` is ALWAYS rate-limit exempt — never add `@limiter.limit()` to it
- Stripe webhook MUST use `stripe.webhooks.construct_event()` for signature verification
- Token packs use `mode="payment"`, course plans use `mode="subscription"`
- `CHECKOUT_MODE` dict in `stripe_service.py` defines which price IDs use which mode
- Webhook secret: missing `STRIPE_WEBHOOK_SECRET` = signature check skipped (local only, never prod)

## Live Endpoints
```
POST /api/stripe/checkout    → creates Stripe Checkout Session, returns {url}
GET  /api/stripe/plans       → lists available plans (60s Redis cache)
POST /api/stripe/webhook     → handles Stripe events (rate-limit EXEMPT)
```

## Key Files
```
backend/app/routes/stripe.py          ← route handlers
backend/app/services/stripe_service.py ← business logic, CHECKOUT_MODE dict
backend/app/services/broski_service.py ← token award on payment
```

## Token Grants (LOCKED — never change these)
| Pack | Price | Tokens |
|------|-------|--------|
| starter | £5 | 200 |
| builder | £15 | 800 |
| hyper | £35 | 2500 |

## Webhook Events Handled
```python
"checkout.session.completed"      → save payment + award BROski$ + set tier
"customer.subscription.deleted"   → cancel subscription
"invoice.payment_failed"          → log warning
"customer.subscription.updated"   → log status change
```

## E2E Test — Run This to Verify

```bash
# Terminal 1 — forward webhooks locally
stripe listen --forward-to localhost:8000/api/stripe/webhook

# Terminal 2 — trigger a test checkout
curl -X POST http://localhost:8000/api/stripe/checkout \
  -H "Content-Type: application/json" \
  -d '{"price_id": "starter", "user_id": "broski_test"}'

# Open the returned URL in browser, use test card:
# Card: 4242 4242 4242 4242 | Exp: any future | CVC: any
```

## Idempotency Pattern
```python
# Webhook handler uses ON CONFLICT DO NOTHING
INSERT INTO payments (...) 
ON CONFLICT (stripe_payment_intent_id) DO NOTHING
```

## .env Keys Required
```env
STRIPE_SECRET_KEY=sk_live_xxx         # or sk_test_xxx for local
STRIPE_WEBHOOK_SECRET=whsec_xxx       # from stripe listen output (local)
STRIPE_PRICE_STARTER=price_xxx
STRIPE_PRICE_BUILDER=price_xxx
STRIPE_PRICE_HYPER=price_xxx
STRIPE_PRICE_PRO_MONTHLY=price_xxx
STRIPE_PRICE_PRO_YEARLY=price_xxx
STRIPE_PRICE_HYPER_MONTHLY=price_xxx
STRIPE_PRICE_HYPER_YEARLY=price_xxx
```

## Debugging Checklist
1. `STRIPE_WEBHOOK_SECRET` set? → signature verification fails silently if missing
2. Webhook endpoint reachable? → `curl http://localhost:8000/api/stripe/webhook` → should return 405 (POST only)
3. Stripe CLI listening? → `stripe listen` output should show "Ready!"
4. Payment lands in DB? → `SELECT * FROM payments ORDER BY created_at DESC LIMIT 5;`
5. BROski$ awarded? → `SELECT broski_tokens FROM users WHERE ...`
