# ⚡ HyperCode V2.0 — Resource Caps & Performance Guide

> Audit ticket: `PERF-001`
> Goal: Full stack runs safely on low-spec hardware (4GB RAM, 4-core CPU)

---

## 📊 Full Stack RAM Budget

All values are idle-state estimates. Active agent inference adds 200–400MB per agent.

| Service | CPU Limit | RAM Limit | RAM Reserve | Priority |
|---|---|---|---|---|
| **redis** | 1.0 | 1 GB | 256 MB | 🔴 Core |
| **postgres** | 1.0 | 1 GB | 256 MB | 🔴 Core |
| **hypercode-core** | 1.0 | 1 GB | 512 MB | 🔴 Core |
| **celery-worker** | 1.0 | 1 GB | 256 MB | 🔴 Core |
| **dashboard** | 0.5 | 512 MB | — | 🔴 Core |
| **hypercode-ollama** | 2.0 | 3 GB | 1 GB | 🟡 Optional |
| **prometheus** | 0.5 | 512 MB | 128 MB | 🟡 Observability |
| **grafana** | 0.5 | 512 MB | 128 MB | 🟡 Observability |
| **node-exporter** | 0.25 | 128 MB | 32 MB | 🟡 Observability |
| **cadvisor** | 0.25 | 256 MB | 64 MB | 🟡 Observability |
| **loki** | 0.5 | 256 MB | 64 MB | 🟡 Observability |
| **tempo** | 0.5 | 256 MB | 64 MB | 🟡 Observability |
| **promtail** | 0.25 | 128 MB | 32 MB | 🟡 Observability |
| **minio** | 0.5 | 512 MB | 128 MB | 🟢 Optional |
| **chroma** | 0.5 | 512 MB | 128 MB | 🟢 Optional |
| **celery-exporter** | 0.25 | 128 MB | 32 MB | 🟢 Optional |
| **broski-bot** | 1.0 | 1 GB | 512 MB | 🟢 Optional |
| Specialist agents (x8) | 0.5 each | 512 MB each | 128 MB each | 🟢 Agents profile |
| **crew-orchestrator** | 0.5 | 512 MB | 256 MB | 🟢 Agents profile |
| **healer-agent** | 0.5 | 512 MB | 256 MB | 🟢 Agents profile |
| **security-scanner** | 0.5 | 512 MB | 64 MB | 🟣 Background |

**Full stack total (all services):** ~12–16 GB RAM — needs 16 GB+ machine
**Core only (no agents, no observability):** ~4.5 GB RAM — needs 8 GB machine
**NANO profile:** ~1.4 GB RAM — safe on 4 GB machine 🌟

---

## 🚀 Usage Profiles

### Full stack (16 GB+ machine)
```bash
docker compose up
```

### Core + Agents (8 GB machine)
```bash
docker compose --profile agents up
```

### Core + Observability only (8 GB machine)
```bash
docker compose up  # No agent profiles
```

### NANO mode (4 GB machine 🌟)
```bash
# Uses cloud LLM — set PERPLEXITY_API_KEY or OPENAI_API_KEY in .env first!
docker compose -f docker-compose.yml -f docker-compose.nano.yml up
```

### Agents-lite (from existing docker-compose.agents-lite.yml)
```bash
docker compose -f docker-compose.agents-lite.yml up
```

---

## 🔍 Monitoring Resource Usage

```bash
# Live container stats
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Check if any container hit its memory limit (OOM killed)
docker inspect <container> | grep OOMKilled

# Full resource usage summary
docker stats --no-stream
```

---

## ⚠️ OOM Prevention Rules

- Never run full stack on < 8 GB RAM without NANO overlay
- Ollama alone needs 1–3 GB depending on model — disable in NANO mode
- Agent specialist containers each add ~300–500 MB when active
- Redis `maxmemory 512mb` is already set in the command — it will evict rather than OOM
- If Postgres OOM kills: reduce `shared_buffers` via `POSTGRES_SHARED_BUFFERS=128MB` env var

---

## 🧠 ND Note

For neurodivergent users on lower-spec machines: the NANO profile is designed so HyperCode
starts in **under 30 seconds** and feels **snappy and responsive**.

A slow, laggy environment is a dopamine-killer. NANO mode = instant feedback = flow state protection. 🔥
