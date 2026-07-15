# HS-037 — Architecture Quick Reference — V2.4

> **Extracted from:** `CLAUDE.md §6` · HyperCode-V2.4
> **Quick lookup for:** Networks, ports, bot cogs, Guardian phases

---

## Networks

```
app-net     → core services (internal)
data-net    → redis, postgres, chroma, minio (internal)
obs-net     → prometheus, grafana, loki, tempo (internal)
agent-net   → all agents
agents-net  → broski-bot + hyper-agents
```

## Key Ports

```
8000  hypercode-core API       8081  crew-orchestrator
8088  hypercode-dashboard      8095  hyperhealth-api
8098  broski-pets-bridge       8099  nemoclaw-agent
9090  prometheus               3001  grafana
3100  loki                     3200  tempo
6379  redis                    5432  postgres
```

## ONE TRUE BOT — broski-bot

**Location:** `agents/broski-bot/` — profile: `discord`
> ⚠️ `discord-bot/` = LEGACY — do NOT use
> ⚠️ Entrypoint is `python -u -m cogs.bot` NOT `main.py`

### Active Cogs

| Cog | Commands |
|---|---|
| `economy` | `/balance` `/daily` `/give` `/rich` |
| `leaderboard` | `/top` `/rank` |
| `ai` | `/ask` (→ Core orchestrator) |
| `focus` | `/focus start\|stop` `/focusstats` |
| `missions` | `/missions` `/missions-claim` |
| `health_check` | `/health` |
| `digest` | `/digest` (admin) + weekly auto-DM |
| `moderation` | passive auto-mod |
| `welcome` | passive on-join |

### Run Commands

```bash
docker compose --profile discord up -d            # bot + core
docker compose --profile discord up -d broski-bot # bot only
.\scripts\launch-bot.ps1                          # preflight → up (recommended)
```

## Guardian Phases

| Phase | Status | What It Does |
|---|---|---|
| P1 | ✅ LIVE | Auto-role on join + `/hyperfocus_setup` |
| P2 | ✅ LIVE | Weekly digest DM |
| P3a | ✅ LIVE | Spam → reversible timeout, `mod_actions` audit |
| P3b | ✅ LIVE | Raid auto-lockdown → reversible channel lock |
| P3c | ✅ BUILT | 3-strike → veto buttons → ban ONLY on explicit APPROVE click |

## 5-Repo Ecosystem Map

```
Hyper-Vibe-Coding-Course ──── manifest.json ────▶ HyperCode-V2.4
        │                                               │
        └──────────── HyperAgent-SDK ──────────────────┘
                              │
                  BROskiPets-LLM-dNFT (port 8098)
                              │
              BROski-Obsidian-Brain (cluster.json)
```

> All repos on-disk: `H:\HYPERFOCUSZONE\HperCore\`
