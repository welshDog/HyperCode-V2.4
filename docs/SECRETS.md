# 🗝️ HyperCode V2.4 — Secrets Management (Phase 10C)

## Why?
No secrets in `.env` files in production. Docker secrets = files on disk, mounted at `/run/secrets/` inside containers. Never in env vars, never in git.

---

## Quick Start (Fresh Setup)

```bash
# 1. Generate all secrets
bash scripts/secrets-init.sh

# 2. Paste real API keys
nano secrets/discord_token.txt
nano secrets/openai_api_key.txt
nano secrets/perplexity_api_key.txt

# 3. Launch with secrets overlay
docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d
```

---

## Secret Files Reference

| File | What | Auto-generated? |
|------|------|-----------------|
| `secrets/postgres_password.txt` | Postgres root password | ✅ Yes |
| `secrets/api_key.txt` | HyperCode master API key (`hc_` prefix) | ✅ Yes |
| `secrets/jwt_secret.txt` | JWT signing secret | ✅ Yes |
| `secrets/memory_key.txt` | Agent memory encryption key | ✅ Yes |
| `secrets/orchestrator_api_key.txt` | Crew orchestrator API key | ✅ Yes |
| `secrets/grafana_admin_password.txt` | Grafana admin password | ✅ Yes |
| `secrets/minio_root_user.txt` | MinIO root username | ✅ Yes (hyperminio) |
| `secrets/minio_root_password.txt` | MinIO root password | ✅ Yes |
| `secrets/discord_token.txt` | Discord bot token | ⚠️ Paste manually |
| `secrets/openai_api_key.txt` | OpenAI API key | ⚠️ Paste manually |
| `secrets/perplexity_api_key.txt` | Perplexity API key | ⚠️ Paste manually |

---

## Rotating Secrets

```bash
# Regenerate ALL auto-generated secrets (keeps manual API keys)
bash scripts/secrets-init.sh --rotate

# Then restart affected services
docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d --force-recreate
```

---

## How Containers Read Secrets

Containers read secrets via `_FILE` environment variable convention:

```python
# Python example — reads /run/secrets/api_key
import os

def get_secret(env_var: str) -> str:
    file_path = os.environ.get(f"{env_var}_FILE")
    if file_path:
        with open(file_path) as f:
            return f.read().strip()
    return os.environ.get(env_var, "")

API_KEY = get_secret("API_KEY")
```

---

## Iron Rules

- ❌ Never commit `secrets/*.txt` — covered by `.gitignore`
- ❌ Never put passwords/tokens in `.env` — only non-sensitive config
- ✅ `.env.example` shows exactly which vars moved to secrets
- ✅ Run `docker compose config` to verify no secrets leak into env
- ✅ `secrets/` folder permissions: `700` (dir) + `600` (files)

---

## Migrating from Old `.env` Secrets

```bash
# 1. Generate new secrets files
bash scripts/secrets-init.sh

# 2. Copy existing values from old .env into secret files
#    (instead of using the auto-generated ones)
nano secrets/postgres_password.txt   # paste old POSTGRES_PASSWORD
nano secrets/api_key.txt             # paste old API_KEY
nano secrets/jwt_secret.txt          # paste old HYPERCODE_JWT_SECRET

# 3. Remove those vars from .env
# 4. Restart with overlay
docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d
```
