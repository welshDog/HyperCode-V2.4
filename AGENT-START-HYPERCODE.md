# 🐳 AGENT-START — HyperCode V2.4 Specific
> Repo-specific boot file for `HyperCode-V2.4`
> Read AGENT-START.md first, then this file.
> Last updated: May 21, 2026

---

## 🎯 THIS REPO'S MISSION

HyperCode V2.4 is the **core autonomous AI infrastructure platform** — 29+ Docker containers, FastAPI backend, 25+ agent swarm, full observability stack.

---

## 📋 READ ORDER FOR THIS REPO

```
1. AGENT-START.md          → universal rules + skill loader
2. CLAUDE.md               → sacred rules for this repo
3. WHATS_DONE.md           → what's built (check before every suggestion)
4. docs/SESSION_REPORT_[latest].md  → last session state
```

---

## ⚡ KEY COMMANDS

```bash
# Start full stack + agents
docker compose --profile agents up -d

# Start with ALL profiles
docker compose --profile agents --profile hyper --profile health up -d

# Start Discord bot
docker compose --profile discord up -d broski-bot

# Verify MCP server live
curl http://localhost:8823/sse

# Run tests
pytest backend/tests -q

# DB migrations
docker compose exec hypercode-core alembic upgrade head

# Pre-build check
make build

# Focus mode (stops 14 non-essential containers)
make focus

# Calm mode (restores all + 75 BROski$)
make calm
```

---

## 🔑 KEY PORTS

| Port | Service |
|------|---------|
| 8000 | hypercode-core API |
| 8081 | crew-orchestrator |
| 8088 | hypercode-dashboard |
| 8823 | hypercode-mcp-server (IDE connection) |
| 8098 | broski-pets-bridge |
| 8099 | nemoclaw-agent |
| 9090 | prometheus |
| 3001 | grafana |
| 6379 | redis |
| 5432 | postgres |

---

## 🧠 SKILLS TO LOAD FOR THIS REPO

```
Working on agents?        → github.com/welshDog/HYPER-SILLs-By-WelshDog/agents/
Working on Docker/infra?  → github.com/welshDog/HYPER-SILLs-By-WelshDog/dev/
Working on BROski bot?    → github.com/welshDog/HYPER-SILLs-By-WelshDog/broski/
Full skill map:           → github.com/welshDog/HYPER-SILLs-By-WelshDog/vault-index.md
```

---

## 🔴 TOP 5 SACRED RULES (full list in CLAUDE.md)

1. **`docker-ce-cli` NEVER `docker.io`** for socket agents
2. **`data-net` + `obs-net` = `internal: true` ALWAYS** — never expose
3. **Redis: DB 1 = cache, DB 2 = rate limits — NEVER mix**
4. **Memory limits on ALL services** — OOM crashed stack Apr 17
5. **Stripe webhook ALWAYS rate-limit exempt**

---

## 🤖 MCP AGENT TOOLS (available in Claude Code)

| Say this in Claude Code | Does this |
|------------------------|----------|
| "List all agents" | Shows all 25+ agents + status |
| "Check system health" | Full stack health check |
| "Create a task: [X]" | Queues task to right agent |
| "Show recent logs" | All agent logs |
| "What's my BROski$ balance?" | Economy check |
| "Generate a plan for [X]" | Runs planning pipeline |

---

## 🚀 NEXT TASKS (from WHATS_DONE.md)

1. Test Claude Code → agent conversation (type "List all agents")
2. Enable Supabase leaked password protection (2 mins)
3. E2E Stripe checkout test
4. BROskiPets Web3 mint E2E on Base Sepolia
5. HyperAgent-SDK v0.4.0 — Web3/dNFT types

---

## 📁 WHERE THINGS LIVE

```
docker-compose.yml          → main stack (includes all others)
docker-compose.agents.yml   → all agents + MCP server
backend/app/main.py         → FastAPI core
agents/                     → all agent code
services/hypercode-mcp-server/ → MCP server (port 8823)
.mcp.json                   → IDE connection config
CLAUDE.md                   → sacred rules
WHATS_DONE.md               → what's built
docs/                       → all documentation
```

---

> 🐶♾️ HyperCode V2.4 — Built by @welshDog
> *"Stop apologising for your brain. Start building."*
