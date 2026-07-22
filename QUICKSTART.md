# ⚡ HYPERCODE V2.4 — NEURO DEV STACK QUICKSTART

> 🟢 ACTIVE — Core of the Neuro Dev Stack. Part of [HyperFocus Zone](https://github.com/welshDog/HyperFocus-Zone-Portal).

**Get the full 48-container neurodivergent-first AI infrastructure running — and connected to your IDE, your Brain, and your Course — in under 15 minutes.**

> 💡 This quickstart is part of the **Neuro Dev Stack v1**: Engine → IDE → Brain → Course → Agents.
> Each step below adds a new layer. You can stop at any step and still have something useful.

---

## 🔧 Prerequisites

- Docker Desktop (must use `docker-ce-cli` — never `docker.io`)
- Git
- Windows PowerShell, Mac, or Linux terminal
- An `.env` file (copy from `.env.example` — full key list in Step 2)

---

## Step 1 — Clone & Enter 🐳

```bash
git clone https://github.com/welshDog/HyperCode-V2.4.git
cd HyperCode-V2.4
```

---

## Step 2 — Set Up Your Environment 🔑

```bash
cp .env.example .env
# Edit .env with your keys — NEVER commit .env!
nano .env   # or code .env / notepad .env
```

**Required keys:**
- `DISCORD_TOKEN` — your BROski bot token
- `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET`
- `REDIS_URL` — default: `redis://localhost:6379`
- `OPENAI_API_KEY` or `ANTHROPIC_API_KEY`

```bash
# Validate .env before launch (catches missing keys)
python scripts/validate_env.py
```

---

## Step 3 — Start Core Services 🚀

```bash
# Core stack (Redis, Postgres, API)
docker compose -f docker-compose.core.yml up -d

# Verify everything is healthy
docker ps --format 'table {{.Names}}\t{{.Status}}'
```

✅ You should see core services as `Up (healthy)`.  
⚠️ Always use `docker-ce-cli` — NEVER `docker.io`

---

## Step 4 — Launch Agents 🤖

```bash
# Full agent stack (48 containers)
docker compose -f docker-compose.agents.yml up -d

# Or lite mode (faster, fewer containers — great for low-RAM machines)
docker compose -f docker-compose.agents-lite.yml up -d
```

---

## Step 5 — Open Your Dashboard 🎯

Visit these URLs once containers are running:

| Interface | URL | What it does |
|---|---|---|
| 🚀 Mission Control | `http://localhost:8088` | Full ops dashboard |
| 🧠 Core API Docs | `http://localhost:8000/api/v1/docs` | FastAPI + Swagger |
| 💻 BROski Terminal | `http://localhost:3000` | ND-first CLI |
| ⚙️ Crew Orchestrator | `http://localhost:8081` | Agent lifecycle |
| ❤️ Healer Agent | `http://localhost:8008` | Self-healing monitor |
| 📊 Grafana | `http://localhost:3001` | Observability stack |

```bash
# Quick health check
curl http://localhost:8000/health
```

---

## Step 6 — Connect HyperFocus IDE 💻 *(Neuro Dev Stack Layer 2)*

Once the engine is running, wire up your IDE:

```bash
# Clone the IDE into a sibling folder
git clone https://github.com/welshDog/HyperFocus-IDE-BROski-v1.git
cd HyperFocus-IDE-BROski-v1

# Point its MCP config at your running HyperCode-V2.4 engine
# Edit .mcp.json → set HYPERCODE_API to http://localhost:8000
code .mcp.json
```

> 📖 See [HyperFocus-IDE-BROski-v1 README](https://github.com/welshDog/HyperFocus-IDE-BROski-v1) for full IDE setup.

---

## Step 7 — Activate Your BROski Brain 🧠 *(Neuro Dev Stack Layer 3)*

Give your whole stack persistent memory:

```bash
git clone https://github.com/welshDog/BROski-Obsidian-Brain-for-HyperFocus-z0ne.git
cd BROski-Obsidian-Brain-for-HyperFocus-z0ne

# Install Python bridge tools
pip install -r requirements.txt

# Start the MCP memory bridge
python mcp_bridge.py
```

Then in your IDE or agent config, add the Obsidian Brain MCP server as a context provider.

> 📖 See [BROski-Obsidian-Brain README](https://github.com/welshDog/BROski-Obsidian-Brain-for-HyperFocus-z0ne) for vault setup.

---

## Step 8 — Learn the Stack 🎓 *(Neuro Dev Stack Layer 4)*

Want to understand what you just built?

**[→ Hyper-Vibe Coding Course](https://github.com/welshDog/Hyper-Vibe-Coding-Course)**

- Built for ADHD, dyslexia, and autistic developers
- Walks you through the entire HyperCode stack from scratch
- Earn BROski$ coins as you complete modules
- Stripe payments, observability, agent building — all covered

---

## Step 9 — Extend with Agent SDK ⚡ *(Neuro Dev Stack Layer 5 — Advanced)*

Build your own agents that plug into the swarm:

```bash
npm install @w3lshdog/hyper-agent
```

> 📖 See [HyperAgent-SDK](https://github.com/welshDog/HyperAgent-SDK) for the full agent manifest standard.

---

## 💜 Sacred Rules (Never Break)

| Rule | ✅ Correct | ❌ Wrong |
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

| Doc | What's inside |
|---|---|
| [`AGENT-START.md`](./AGENT-START.md) | Agent session startup |
| [`OPERATIONS.md`](./OPERATIONS.md) | Full ops runbook |
| [`PORT_MAP_COMPLETE.md`](./PORT_MAP_COMPLETE.md) | All 48 container ports |
| [`WHATS_DONE.md`](./WHATS_DONE.md) | Completed features tracker |
| [`RUNBOOK.md`](./RUNBOOK.md) | Incident response |
| [`START_HERE.md`](./START_HERE.md) | MCP Gateway + Model Runner |

---

## 🗺️ The Full Neuro Dev Stack

| Layer | Repo | Role |
|---|---|---|
| 1 — Engine | [HyperCode-V2.4](https://github.com/welshDog/HyperCode-V2.4) | 48-agent swarm + API |
| 2 — IDE | [HyperFocus-IDE-BROski-v1](https://github.com/welshDog/HyperFocus-IDE-BROski-v1) | ND-first coding surface |
| 3 — Brain | [BROski-Obsidian-Brain](https://github.com/welshDog/BROski-Obsidian-Brain-for-HyperFocus-z0ne) | Persistent AI memory |
| 4 — Course | [Hyper-Vibe Coding Course](https://github.com/welshDog/Hyper-Vibe-Coding-Course) | Learn + earn BROski$ |
| 5 — Agents | [HyperAgent-SDK](https://github.com/welshDog/HyperAgent-SDK) | Build + extend agents |

> 🚪 **Ecosystem front door:** [HyperFocus-Zone-Portal](https://github.com/welshDog/HyperFocus-Zone-Portal)

---

> Built in Llanelli, South Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁥 by [@welshDog](https://github.com/welshDog) | BROski♾️
