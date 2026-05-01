# 🔧 Railway Troubleshooting — Debug & Fix Guide

## 🚨 TRIAGE CHECKLIST (Run This First!)

When something is broken on Railway, run this mental checklist:

1. ✅ `railway link` — are you linked to the right project/service?
2. ✅ `railway variable` — are all required env vars present?
3. ✅ `railway logs --tail 200` — what's the actual error?
4. ✅ Is a `Dockerfile` present? Is it valid?
5. ✅ Is `PORT` configured correctly?
6. ✅ Is the correct environment selected? (`railway environment`)

---

## ❌ Error: `Service not found`

**Cause:** CLI isn't linked to a Railway project/service.

**Fix:**
```bash
railway link                    # Interactive linker — picks your project
railway link --project <id>     # Link by project ID
railway status                  # Verify you're linked correctly
```

---

## ❌ Build Fails / Nixpacks Error

**Cause:** Railway's auto-builder (nixpacks) can't detect your stack, or your Dockerfile has issues.

**Fixes:**

1. Add a `Dockerfile` — Railway prioritises it over nixpacks:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

2. Or add a `nixpacks.toml` to force stack detection:
```toml
[phases.setup]
nixPkgs = ["python311", "pip"]

[start]
cmd = "uvicorn main:app --host 0.0.0.0 --port $PORT"
```

3. Check Railway build logs carefully — nixpacks tells you exactly what it tried.

---

## ❌ Env Vars Missing at Runtime

**Cause:** Variables not set, or set in wrong environment.

**Fix:**
```bash
railway variable                           # List all vars — check for gaps
railway variable --set KEY=VALUE           # Add missing vars
railway environment                        # Make sure you're in the right env
railway redeploy                           # Redeploy to pick up new vars
```

---

## ❌ Port Not Exposed / Connection Refused

**Cause:** App not listening on the right port, or Railway can't detect it.

**Fix:**
- Railway injects `PORT` automatically. Your app **MUST** bind to `$PORT`, not a hardcoded port.

```python
# FastAPI — correct
import os
uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
```

```javascript
// Express — correct
const port = process.env.PORT || 3000;
app.listen(port);
```

- Explicitly set: `railway variable --set PORT=8000`
- Check: Service Settings → Networking → make sure HTTP port is set

---

## ❌ Volume Data Lost After Redeploy

**Cause:** Data was written to ephemeral storage (not a volume). Redeploying wipes it.

**Fix:**
1. Dashboard → Service → **Add Volume**
2. Mount path: `/data` (or wherever your app writes)
3. Update app config to write to `/data/` instead of local directory

```bash
railway volume add   # Adds persistent volume
```

Your data now survives redeployments. ✅

---

## ❌ SSH Not Working

**Cause:** SSH command not copied correctly, or service isn't running.

**Fix:**
1. Railway Dashboard → Service → right-click → **SSH** → copy the exact command
2. Make sure the service is actually running (not crashed)
3. Check `railway logs` first — if the service is crash-looping, SSH won't work

---

## ❌ `railway up` Is Slow / Times Out

**Cause:** Uploading too many files (node_modules, .git, etc.)

**Fix — Add `.railwayignore`:**
```
node_modules/
.git/
__pycache__/
*.pyc
dist/
.pytest_cache/
.venv/
venv/
*.egg-info/
```

This cuts upload size from gigabytes to megabytes. Huge speed boost. ✅

---

## ❌ Service Keeps Restarting / Crash Loop

**Cause:** App is crashing on startup.

**Debug Steps:**
```bash
railway logs --tail 200     # Read the actual error
railway ssh                 # SSH in if it's staying up long enough
```

**Common causes:**
- Missing env var → app throws on startup
- Wrong `CMD` in Dockerfile
- Port binding error (see Port section above)
- Database not ready yet → add retry logic or health checks

**Quick test:**
```bash
railway run python main.py  # Run locally with Railway env vars injected
```
If it crashes here too, the bug is in your code, not Railway config.

---

## ❌ Database Connection Failing

**Cause:** Wrong connection string, SSL issue, or database not ready.

**Fix:**
```bash
railway variable                    # Check DATABASE_URL is set
railway connect postgresql          # Test direct connection
```

For SSL issues (common with Supabase + Railway):
```python
# Add SSL mode to connection string
DATABASE_URL = os.environ["DATABASE_URL"] + "?sslmode=require"
```

If using an external DB (e.g. Supabase), make sure:
- IP allowlist includes Railway's egress IPs (or use connection pooler)
- Use `?sslmode=require` in the URL

---

## ❌ Custom Domain Not Working

**Cause:** DNS not propagated, or domain not added correctly.

**Fix:**
```bash
railway domain                      # List domains
railway domain add yourdomain.com   # Add domain
```

Then in your DNS provider:
- Add CNAME record: `@` → your Railway domain (shown in dashboard)
- Wait 1–48 hours for DNS propagation

Railway auto-provisions SSL via Let's Encrypt once DNS resolves. ✅

---

## ❌ GitHub Auto-Deploy Not Triggering

**Cause:** Wrong branch linked, or webhook disconnected.

**Fix:**
1. Dashboard → Service → Settings → **Source** → verify branch is correct
2. Disconnect and reconnect GitHub repo if webhook seems stuck
3. Check GitHub repo → Settings → Webhooks → verify Railway webhook is active and getting `200` responses

---

## 🧰 GENERAL DEBUG TOOLKIT

```bash
# Full log dump
railway logs --tail 500 > debug.log

# Live log streaming while you test
railway logs &

# Inject Railway vars locally and run
railway run python -c "import os; print(os.environ)"   # Check all vars

# Open psql directly
railway connect postgresql

# Full status overview
railway status
```

---

## 💡 NEURODIVERGENT-FRIENDLY DEBUG FLOW

When you're overwhelmed and don't know where to start:

1. **ONE thing at a time.** Start with logs: `railway logs --tail 100`
2. **Find the first red line.** That's your clue — ignore everything after it.
3. **Google the exact error message** + "Railway" — their docs and community are solid.
4. **Test locally first:** `railway run <your-command>` — if it breaks here, it's code not Railway.
5. **Ask for help** — Railway Discord is active and friendly.

You've got this. 🤟
