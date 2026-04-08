# 🎭 Crew Orchestrator — Agent Lifecycle Guide

> **Port:** 8081
> **Role:** Manages agent lifecycle + task execution pipelines
> **Last Updated:** 2026-03-25

---

## 🧠 What is the Crew Orchestrator?

The Crew Orchestrator is the **team manager** of HyperCode. It keeps track of every agent, assigns tasks to them, monitors their progress, and makes sure work gets done.

Think of it like:
> 🎬 "Director of the movie — keeps all actors (agents) on their marks."

---

## ⚡ Quick Start

### Check Crew is running:
```bash
curl http://localhost:8081/health
```

### List all agents in the crew:
```bash
curl http://localhost:8081/agents
```

### Assign a task to the crew:
```bash
curl -X POST http://localhost:8081/tasks/assign \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "task-001",
    "agent_type": "coder",
    "priority": "high",
    "payload": { "instruction": "Write a Python function to parse JSON" }
  }'
```

---

## 🏗️ Task Flow

```
New Task Created (API or BROski Terminal)
         ↓
   Crew Orchestrator receives task
         ↓
   Finds best available agent (by type + load)
         ↓
   Assigns task to agent
         ↓
   Agent executes + streams results
         ↓
   Results stored in PostgreSQL
         ↓
   Task marked complete ✅
         ↓
   BROski$ coins awarded 💰
```

---

## 👥 Agent Types Supported

| Type | What it does |
|------|--------------|
| `coder` | Writes, reviews, refactors code |
| `researcher` | Web research + summarisation |
| `planner` | Breaks down complex tasks |
| `devops` | CI/CD, Docker, infra tasks |
| `healer` | Monitors + fixes services |
| `custom` | Any new type Agent X creates |

---

## ⚙️ Configuration

`agents/crew_orchestrator/config.yaml`:
```yaml
crew_orchestrator:
  port: 8081
  max_concurrent_tasks: 10
  task_timeout_seconds: 300
  agent_x_url: http://localhost:8090
  healer_url: http://localhost:8008
  database_url: postgresql://hypercode:password@localhost:5432/hypercode
  redis_url: redis://localhost:6379
  spawn_on_demand: true
```

---

## 📊 Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/agents` | List all crew agents |
| GET | `/tasks` | List all tasks |
| POST | `/tasks/assign` | Assign task to agent |
| GET | `/tasks/{id}` | Get task status |
| DELETE | `/tasks/{id}` | Cancel task |
| GET | `/metrics` | Crew performance metrics |

---

## 🚨 Troubleshooting

| Problem | Fix |
|---------|-----|
| Tasks queuing but not running | Check agents are registered: `GET /agents` |
| Agent not picking up tasks | Restart agent container |
| Task timeout | Increase `task_timeout_seconds` in config |
| Crew down | `docker restart crew-orchestrator` |

---
> **built with WelshDog + BROski 🚀🌙**
