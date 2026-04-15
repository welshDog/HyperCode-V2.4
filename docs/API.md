# API Reference 🔌

> **HyperCode V2.4 — FastAPI Backend**
> **Base:** `http://localhost:8000/api/v1`
> **Swagger UI:** `http://localhost:8000/api/v1/docs`
> **Last Updated:** 2026-04-15

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

## 💳 Stripe Payments (Phase 10F)

> Base path: `/api/stripe` (no `/api/v1` prefix)

### List Available Plans
- **GET** `/api/stripe/plans`
- **Auth:** None required

```json
{
  "plans": ["starter", "builder", "hyper", "pro_monthly", "pro_yearly", "hyper_monthly", "hyper_yearly"]
}
```

### Create Checkout Session
- **POST** `/api/stripe/checkout`
- **Auth:** Optional (pass `user_id` to link to account)

**Request:**
```json
{
  "price_id": "starter",
  "user_id": "broski_user_123"
}
```

**Response:**
```json
{
  "checkout_url": "https://checkout.stripe.com/pay/cs_live_...",
  "session_id": "cs_live_..."
}
```

**Price keys:**
| Key | Type | Price |
|-----|------|-------|
| `starter` | one-time | £5 / 200 tokens |
| `builder` | one-time | £15 / 800 tokens |
| `hyper` | one-time | £35 / 2500 tokens |
| `pro_monthly` | subscription | £9/mo |
| `pro_yearly` | subscription | £90/yr |
| `hyper_monthly` | subscription | £29/mo |
| `hyper_yearly` | subscription | £290/yr |

### Stripe Webhook
- **POST** `/api/stripe/webhook`
- **Auth:** Stripe signature (header `Stripe-Signature`) — NOT rate-limited

Events handled: `checkout.session.completed`, `customer.subscription.deleted`, `customer.subscription.updated`, `invoice.payment_failed`

---

## 🔑 Agent API Keys (Phase 10D)

### Create Agent Key
- **POST** `/api/v1/agent-keys`
- **Auth:** JWT required
- **Body:** `{ "name": "my-agent", "scopes": ["execute", "read"] }`

**Response:**
```json
{
  "key": "hc_aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789012",
  "key_id": "uuid-...",
  "name": "my-agent"
}
```

Keys use `hc_` prefix + 43 URL-safe chars. Shown **once** at creation — store it.

### List Agent Keys
- **GET** `/api/v1/agent-keys`
- **Auth:** JWT required

### Revoke Agent Key
- **DELETE** `/api/v1/agent-keys/{key_id}`
- **Auth:** JWT required

---

## 🔌 WebSocket Endpoints

### CognitiveUplink — `WS /ws/uplink`

Neural interface bridging the Mission Control chat UI to the Crew Orchestrator.

**Connect:** `ws://localhost:8000/ws/uplink`

**Inbound messages:**
```json
// Ping / keepalive
{ "type": "ping" }

// Execute a command
{ "type": "execute", "id": "optional-task-id", "payload": { "command": "build login page" } }

// Route to a specific agent
{ "type": "execute", "payload": { "command": "@backend-specialist build auth module" } }
```

**Outbound messages:**
```json
// Ping reply
{ "type": "pong" }

// Successful dispatch
{ "type": "response", "payload": "✅ Command dispatched...\nTask ID: `uplink-abc123`" }

// Agent result
{ "type": "response", "payload": "**[backend-specialist]**\nAuth module scaffolded ✅" }

// Error
{ "type": "error", "data": "Orchestrator timed out (>60s). Task may still be running." }
```

**Other WS endpoints** (real-time data broadcast):

| Path | Purpose |
|------|---------|
| `WS /ws/metrics` | 5-second MetricsSnapshot broadcast |
| `WS /ws/agents` | Agent heartbeat status stream |
| `WS /ws/events` | Live event stream |
| `WS /ws/logs` | Live log stream |
| `WS /api/v1/orchestrator/ws/approvals` | Approval gate pub/sub (Redis) |

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
