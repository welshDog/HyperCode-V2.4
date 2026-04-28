# 🚂 Railway Environment Variables — HyperCode V2.4

Add these to your `hypercode-core` service → Variables tab.

## Required (App won't start without these)

```
ENVIRONMENT=production
HYPERCODE_DB_URL=${{Postgres.DATABASE_URL}}
HYPERCODE_REDIS_URL=${{Redis.REDIS_URL}}
HYPERCODE_JWT_SECRET=<generate: openssl rand -hex 32>
```

## Stripe (needed for payments)

```
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
COURSE_SYNC_SECRET=<same value as in Supabase Edge Function>
```

## Optional (skip if no credits yet)

```
# OPENROUTER_API_KEY=sk-or-...
# ANTHROPIC_API_KEY=sk-ant-...
# DEFAULT_LLM_MODEL=claude-3-haiku-20240307
```

## Railway Reference Syntax

In Railway Variables, you can reference other service vars like:
- `${{Postgres.DATABASE_URL}}` — auto-injects Postgres URL
- `${{Redis.REDIS_URL}}` — auto-injects Redis URL

## Smoke Test

Once deployed:
```bash
curl https://YOUR_DOMAIN.railway.app/health
# Expected: {"status": "healthy"}
```
