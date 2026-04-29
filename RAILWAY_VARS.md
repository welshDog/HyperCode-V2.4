# 🚂 Railway Environment Variables — HyperCode V2.4

Add these to your `HyperCode-V2.4` service → Variables tab.

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

## Railway CLI (Logs + Pause/Resume)

If `railway link` fails on Windows with `No linked project found` / `os error 2`, target the project directly via env vars:

```powershell
$env:RAILWAY_PROJECT_ID="3d66bd92-cac3-4fde-ae9a-07f269b58791"
$env:RAILWAY_ENVIRONMENT_ID="92291c6e-89d8-4a0b-af03-046ca3c30824"
$env:RAILWAY_SERVICE_ID="6ba8816d-7f07-4f83-8fdd-682743edef6b"

railway logs --latest -n 100
railway logs --latest -n 100 --filter "@level:error"
railway logs
```

Pause the service until you’re ready to continue (scale to 0):

```powershell
$env:RAILWAY_PROJECT_ID="3d66bd92-cac3-4fde-ae9a-07f269b58791"
railway scale -s 6ba8816d-7f07-4f83-8fdd-682743edef6b -e 92291c6e-89d8-4a0b-af03-046ca3c30824 --europe-west4-drams3a 0
```

Resume tomorrow (scale back to 1):

```powershell
$env:RAILWAY_PROJECT_ID="3d66bd92-cac3-4fde-ae9a-07f269b58791"
railway scale -s 6ba8816d-7f07-4f83-8fdd-682743edef6b -e 92291c6e-89d8-4a0b-af03-046ca3c30824 --europe-west4-drams3a 1
```

## Known Deployment Gotcha (Alembic)

If deploy logs show:

`psycopg2.errors.DuplicateObject: type "transactiontype" already exists`

That’s from the `001_broski_token_system` migration. The repo fix is in [001_broski_token_system.py](backend/alembic/versions/001_broski_token_system.py) (Postgres ENUM creation made idempotent). Redeploy after pulling the latest code so migrations run cleanly.
