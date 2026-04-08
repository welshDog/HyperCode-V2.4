# ✅ Phase 3 DONE Contract — Agent Activation
> Generated from real compose + orchestrator source. Every command is verified.

---

## 🧭 Port Reference (Authoritative)

| Service             | Host URL                        | Notes                      |
|---------------------|---------------------------------|----------------------------|
| Core API            | http://127.0.0.1:8000/health    | Localhost-only             |
| Crew Orchestrator   | http://127.0.0.1:8081/health    | No auth required           |
| Healer Agent        | http://127.0.0.1:8010/health    | Maps 8010 → internal 8008  |
| System Architect    | http://127.0.0.1:8008/health    | Debug-only host binding    |
| Mission Control     | http://127.0.0.1:8088           | Localhost-only             |

> ⚠️ "Agent X" = meta concept only. No container. Validate via Orchestrator roster instead.

---

## 🚀 Step-by-Step Runbook

### Step 1 — Boot with agents profile

```powershell
docker compose -f docker-compose.yml -f docker-compose.demo.yml --profile agents up -d --no-build
```

### Step 2 — Confirm Orchestrator is alive (no auth needed)

```powershell
curl http://127.0.0.1:8081/health
```

✅ Expected: `{"status":"ok","service":"crew-orchestrator"}`

### Step 3 — Check agent roster

If `ORCHESTRATOR_API_KEY` is unset, `/agents` runs in dev mode (no header required). If it is set, include header: `X-API-Key: <value>`.

```powershell
curl http://127.0.0.1:8081/agents
```

✅ Expected: JSON array with the configured agent roster.

### Step 4 — Confirm Healer is alive (correct port = 8010)

```powershell
curl http://127.0.0.1:8010/health
```

✅ Expected: `{"status":"ok" ...}` (service-specific fields may differ)

### Step 5 — Seed DB

```powershell
docker exec hypercode-core python seed_data.py
```

### Step 6 — Fire smoke task (requires_approval: false)

```powershell
curl -X POST http://127.0.0.1:8081/execute `
  -H "Content-Type: application/json" `
  -d '{
    "task": {
      "id": "phase3-smoke-001",
      "type": "smoke_test",
      "description": "Phase 3 activation smoke test - return status message",
      "agent": "project_strategist",
      "requires_approval": false
    }
  }'
```

✅ Expected: `{"status":"completed",...}` or `{"status":"error",...}` (error usually indicates agent not up yet)

### Step 7 — Verify task logged

```powershell
curl http://127.0.0.1:8081/tasks
```

✅ Expected: array includes `phase3-smoke-001` with `"status":"completed"`.

---

## ✅ Phase 3 DONE Checklist

- All expected agents appear in `GET /agents`
- Orchestrator `GET /health` returns 200
- Healer `GET /health` returns 200 on port 8010
- DB seed completes without errors
- Smoke task completes and appears in `GET /tasks`
