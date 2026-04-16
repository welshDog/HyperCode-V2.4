# Dashboard WebSocket Endpoints
# HyperCode V2.4 | BROski♾

All 4 WebSocket endpoints are served from `hypercode-core` on port **8000**.

---

## Endpoints

| Endpoint | File | Redis source | Purpose |
|---|---|---|---|
| `WS /ws/uplink` | `ws/uplink.py` | crew-orchestrator HTTP | CognitiveUplink neural interface |
| `WS /api/v1/ws/agents` | `ws/agents_broadcaster.py` | `agents:heartbeat:*` HSET keys | Agent online/offline heartbeat (5s poll) |
| `WS /api/v1/ws/events` | `ws/events_broadcaster.py` | `hypercode:events` list + pub/sub | Live system event stream |
| `WS /api/v1/ws/logs` | `ws/logs_broadcaster.py` | `hypercode:logs` list + pub/sub | Live log stream |

---

## Redis Keys

| Key | Type | Written by | Read by |
|---|---|---|---|
| `agents:heartbeat:{name}` | HSET (TTL 30s) | Each agent every 10s | `/ws/agents` |
| `hypercode:events` | RPUSH list (capped 500) | `POST /api/v1/events` | `/ws/events` |
| `hypercode:events:channel` | pub/sub | `POST /api/v1/events` | `/ws/events` |
| `hypercode:logs` | RPUSH list (capped 1000) | HTTP metrics middleware in `main.py` | `/ws/logs` |
| `hypercode:logs:channel` | pub/sub | agents/services | `/ws/logs` |

---

## JavaScript Examples

### /ws/uplink — CognitiveUplink

```js
const ws = new WebSocket("ws://localhost:8000/ws/uplink");

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: "execute",
    id: "cmd-001",
    payload: { command: "@healer check all containers" }
  }));
};

ws.onmessage = (e) => {
  const msg = JSON.parse(e.data);
  // msg.type: "response" | "result" | "error" | "pong"
  console.log(msg.payload);
};

// Keepalive
setInterval(() => ws.send(JSON.stringify({ type: "ping" })), 30_000);
```

### /ws/agents — Agent Heartbeat

```js
const ws = new WebSocket("ws://localhost:8000/api/v1/ws/agents");

ws.onmessage = (e) => {
  const { agents, updatedAt } = JSON.parse(e.data);
  // agents: [{ id, name, status, last_seen }]
  // status: "online" | "offline" | "busy" | "error"
  console.log(`${agents.length} agents — updated ${updatedAt}`);
};
```

Broadcast interval: **5 seconds**. Agents with no heartbeat in 30s vanish from the list (TTL expiry).

### /ws/events — Live Event Stream

```js
const ws = new WebSocket("ws://localhost:8000/api/v1/ws/events");

ws.onopen = () => {
  // Server immediately seeds last 20 events
};

ws.onmessage = (e) => {
  const frame = JSON.parse(e.data);
  // frame.channel: "ws_tasks"
  // frame.data: { id, channel, agentId, taskId, status, payload, timestamp }
  console.log(frame.data);
};
```

Publish an event (internal use — agents/healer call this):

```js
fetch("/api/v1/events", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    channel: "agent",
    agentId: "healer-agent",
    status: "success",
    payload: { message: "Container restarted OK" }
  })
});
```

### /ws/logs — Live Log Stream

```js
const ws = new WebSocket("ws://localhost:8000/api/v1/ws/logs");

ws.onopen = () => {
  // Server immediately sends last 20 log entries as logs:history frames
};

ws.onmessage = (e) => {
  const frame = JSON.parse(e.data);
  // frame.channel: "logs:history" | "logs:live"
  // frame.data: { id, time, agent, level, msg }
  // level: "info" | "warn" | "error" | "success"
  console.log(`[${frame.data.level}] ${frame.data.agent}: ${frame.data.msg}`);
};
```

---

## REST Companions

Each WS endpoint has a matching REST endpoint for initial page load:

| REST | Returns |
|---|---|
| `GET /api/v1/agents/status` | `AgentStatusList` JSON |
| `GET /api/v1/events` | SSE stream (text/event-stream) |
| `GET /api/v1/logs?limit=80` | `LogResponse` JSON (no auth) |

---

## Router Registration

Routers are registered in `backend/app/api/api.py` via `api_router` (mounted at `/api/v1`).
`/ws/uplink` is mounted directly on `app` in `main.py` (no `/api/v1` prefix — matches `CognitiveUplink.tsx`).
