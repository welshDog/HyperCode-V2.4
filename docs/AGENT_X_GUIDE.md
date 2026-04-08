# 🦅 Agent X — Meta-Architect Guide

> **Codename:** Agent X
> **Role:** Autonomous agent designer, deployer & evolver
> **Port:** 8090
> **Last Updated:** 2026-03-25

---

## 🧠 What is Agent X?

Agent X is the **brain of the brain**. It doesn't just run tasks — it **designs, spawns and evolves other AI agents** autonomously using Docker Model Runner.

Think of it like this:
- 🐣 You describe what you need → Agent X builds an agent for it
- 🔁 Agents can self-upgrade via the Evolutionary Pipeline
- 🧬 New agent DNA (configs, prompts, tools) are generated on-the-fly

---

## ⚡ Quick Start

### Check Agent X is running:
```bash
curl http://localhost:8090/health
```

### Spawn a new agent via API:
```bash
curl -X POST http://localhost:8000/api/v1/agents/spawn \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_type": "coder",
    "name": "my-coder-agent",
    "model": "tinyllama",
    "config": {}
  }'
```

### List all active agents:
```bash
curl http://localhost:8000/api/v1/agents/ \
  -H "Authorization: Bearer <token>"
```

---

## 🏗️ How It Works

```
You → Agent X API
         ↓
   Docker Model Runner (local LLM)
         ↓
   Agent Blueprint Generated
         ↓
   New Container Spawned
         ↓
   Crew Orchestrator Registers Agent
         ↓
   Agent starts working on tasks!
```

---

## 🐳 Docker Model Runner Integration

Agent X uses **Docker Model Runner** to run local LLMs — no cloud needed!

- Default model: **TinyLlama** (fast, lightweight)
- Fallback: **Mistral 7B**, **Phi-2**
- OpenAI-compatible API endpoint: `http://localhost:11434/v1`

### Set model in config:
```yaml
agent_x:
  default_model: tinyllama
  fallback_model: mistral
  api_base: http://localhost:11434/v1
```

---

## 🔁 Evolutionary Pipeline

Agent X can **upgrade agents autonomously**:

1. Agent reports performance metrics to Grafana
2. Agent X analyses metrics via LLM
3. New agent config/code is generated
4. Old container is replaced with upgraded version
5. Healer Agent monitors the transition

> ⚠️ **Note:** Evolutionary upgrades are logged in `docs/agents/` folder

---

## 🛠️ Configuration

`agents/agent_x/config.yaml`:
```yaml
agent_x:
  port: 8090
  crew_orchestrator_url: http://localhost:8081
  healer_url: http://localhost:8008
  model_runner_url: http://localhost:11434/v1
  max_agents: 20
  evolution_enabled: true
  evolution_interval_hours: 24
```

---

## 🚨 Troubleshooting

| Problem | Fix |
|---------|-----|
| Agent X not responding | `docker restart agent-x` |
| Spawn fails | Check Docker Model Runner is running on port 11434 |
| Evolution loop crash | Set `evolution_enabled: false` temporarily |
| Agent stuck | Healer Agent will auto-recover within 60s |

---
> **built with WelshDog + BROski 🚀🌙**
