# API Reference 🔌

> **HyperCode V2.0 — FastAPI Backend**
> **Base:** `http://localhost:8000/api/v1`
> **Swagger UI:** `http://localhost:8000/docs`
> **Last Updated:** 2026-03-25

---

## 🔐 Authentication

Most endpoints require a Bearer token:
```
Authorization: Bearer <your_token>
```

### Login
- **POST** `/auth/login/access-token`
- **Body:** `application/x-www-form-urlencoded`

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login/access-token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data "username=admin@hypercode.ai&password=adminpassword"
```

**Response:**
```json
{ "access_token": "<JWT>", "token_type": "bearer" }
```

---

## 📋 Tasks

### Create Task
- **POST** `/tasks/`
- **Auth:** Required

```json
{
  "title": "Task Title",
  "description": "Code content or instruction",
  "priority": "high",
  "type": "translate",
  "project_id": 1
}
```

### Get Tasks
- **GET** `/tasks/`
- **Query Params:** `skip`, `limit`
- **Auth:** Required

### Get Task by ID
- **GET** `/tasks/{task_id}`
- **Auth:** Required

### Update Task
- **PUT** `/tasks/{task_id}`
- **Auth:** Required

### Delete Task
- **DELETE** `/tasks/{task_id}`
- **Auth:** Required

---

## 🤖 Agents

### List All Agents
- **GET** `/agents/`
- **Auth:** Required
- **Response:** Array of active agent objects with status

### Get Agent Status
- **GET** `/agents/{agent_id}/status`
- **Auth:** Required

```json
{
  "agent_id": "agent-x-001",
  "status": "running",
  "uptime_seconds": 3600,
  "last_heartbeat": "2026-03-25T15:00:00Z"
}
```

### Spawn New Agent
- **POST** `/agents/spawn`
- **Auth:** Required

```json
{
  "agent_type": "coder",
  "name": "my-agent",
  "model": "tinyllama",
  "config": {}
}
```

### Kill Agent
- **DELETE** `/agents/{agent_id}`
- **Auth:** Required

---

## 🩺 Health Checks

### System Health
- **GET** `/health`
- **Auth:** None required

```json
{
  "status": "healthy",
  "version": "2.1.0",
  "services": {
    "database": "ok",
    "redis": "ok",
    "agent_x": "ok",
    "healer": "ok"
  }
}
```

### Deep Health (all services)
- **GET** `/health/deep`
- **Auth:** Required

---

## 🧠 MCP Gateway

### List MCP Tools
- **GET** `/mcp/tools`
- **Auth:** Required

### Execute MCP Tool
- **POST** `/mcp/execute`
- **Auth:** Required

```json
{
  "tool_name": "read_file",
  "parameters": { "path": "/app/src/main.py" }
}
```

---

## 📊 Metrics

### Get System Metrics
- **GET** `/metrics/system`
- **Auth:** Required

### Get Agent Metrics
- **GET** `/metrics/agents`
- **Auth:** Required

---

## 🔗 Service Ports Quick Reference

| Service | Port | URL |
|---------|------|-----|
| HyperCode Core API | 8000 | http://localhost:8000 |
| BROski Terminal | 3000 | http://localhost:3000 |
| Crew Orchestrator | 8081 | http://localhost:8081 |
| Healer Agent | 8008 | http://localhost:8008 |
| Mission Control | 8088 | http://localhost:8088 |
| Grafana | 3001 | http://localhost:3001 |

---
> **built with WelshDog + BROski 🚀🌙**
