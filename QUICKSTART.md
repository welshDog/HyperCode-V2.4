# ⚡ HYPERCODE V2.4 — QUICKSTART

> Get the full 48-container neurodivergent-first AI infrastructure running in 5 steps.

---

## Step 1 — Clone & Enter

```bash
git clone https://github.com/welshDog/HyperCode-V2.4.git
cd HyperCode-V2.4
```

---

## Step 2 — Set Up Your Environment

```bash
cp .env.example .env
# Edit .env with your keys — NEVER commit .env!
nano .env
```

**Required keys:**
- `DISCORD_TOKEN` — your BROski bot token
- `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET`
- `REDIS_URL` — default: `redis://localhost:6379`
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`

---

## Step 3 — Start Core Services

```bash
# Core stack (Redis, Postgres, API)
docker compose -f docker-compose.core.yml up -d

# Verify everything is healthy
docker ps --format 'table {{.Names}}\t{{.Status}}'
```

⚠️ Always use `docker-ce-cli` — NEVER `docker.io`

---

## Step 4 — Launch Agents

```bash
# Full agent stack (48 containers)
docker compose -f docker-compose.agents.yml up -d

# Or lite mode (faster, fewer containers)
docker compose -f docker-compose.agents-lite.yml up -d
```

**BROski Discord Bot:**
```bash
cd agents/broski-bot
python -u -m cogs.bot
```

---

## Step 5 — Open Your Dashboard

```bash
# Open in browser
open broski-command-centre.html
# or
open hypercode-docker-dashboard.html
```

Or visit: `http://localhost:8080` (if running dashboard container)

---

## 💜 Sacred Rules (Never Break)

| Rule | Correct | Wrong |
|---|---|---|
| Docker socket | `docker-ce-cli` | `docker.io` |
| Python imports | `from app.X import Y` | `from backend.app.X` |
| Bot library | `discord.py==2.4.0` | `py-cord` |
| Bot entrypoint | `python -u -m cogs.bot` | `python main.py` |
| Frontend dev | `npm run dev:frontend` | `npm run dev` |
| Redis cache | DB 1 | DB 2 |
| Redis rate limits | DB 2 | DB 1 |
| .env files | `.gitignore`'d always | NEVER committed |

---

## 🧠 Full Docs

- [`AGENT-START.md`](./AGENT-START.md) — agent session startup
- [`OPERATIONS.md`](./OPERATIONS.md) — full ops runbook
- [`PORT_MAP_COMPLETE.md`](./PORT_MAP_COMPLETE.md) — all 48 container ports
- [`WHATS_DONE.md`](./WHATS_DONE.md) — completed features tracker
- [`RUNBOOK.md`](./RUNBOOK.md) — incident response

---

> Built in Llanelli, South Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁥 by @welshDog | BROski♾️
