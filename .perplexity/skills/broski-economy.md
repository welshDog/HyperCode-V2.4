---
name: broski-economy
description: Use for BROski$ token economy — awarding tokens, checking balances, Stripe sync, ledger queries, token shop, or economy debugging. Triggers on: "BROski$", "tokens", "award", "balance", "economy", "token shop", "ledger", "earn".
---

# 💰 BROski$ Economy Skill

## Token Tables (Supabase / Postgres)
- `public.users.broski_tokens` — live balance
- `public.token_transactions` — append-only ledger (never edit, only INSERT)
- `award_tokens()` + `spend_tokens()` — SECURITY DEFINER, server-side only

## Award Endpoints
```bash
# Award from course event (idempotent)
POST /api/v1/economy/award-from-course
Header: X-Sync-Secret: <COURSE_WEBHOOK_SECRET>

# Award BROski$ (general)
POST /api/v1/broski/award

# Git commit hook auto-awards
# fix: = 25 BROski$ | docs: = 5 BROski$ | fallback = 10 BROski$
```

## Stripe Tier Grants
- starter = 200 BROski$
- builder = 800 BROski$
- hyper = 2500 BROski$

## Focus Mode Award
- `make calm` → awards 75 BROski$ if session > 10 mins
- Reads DISCORD_USER_ID from .env (add this if missing!)
- Graceful fallback if core is offline

## Idempotency
- CourseSyncEvent model — source_id = git_<sha> or stripe_<id>
- ON CONFLICT (stripe_payment_intent_id) DO NOTHING
- NEVER double-award — always check source_id first

## Pending Manual Steps
- [ ] Register Supabase DB Webhook: token_transactions → INSERT → sync-tokens-to-v24
- [ ] Set COURSE_WEBHOOK_SECRET in V2.4 .env + Supabase Edge Function
- [ ] Add DISCORD_USER_ID=<your_id> to .env

## Debug Commands
```bash
# Check token balance via API
curl http://localhost:8000/api/v1/broski/balance -H "X-API-Key: <key>"

# Check Stripe webhook is receiving
stripe listen --forward-to http://127.0.0.1:8000/api/stripe/webhook
```
