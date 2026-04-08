# Healer Agent

Autonomous healing service for agents and systems. Listens for critical alerts and executes recovery actions with retries, backoff, and audit logging.

## Endpoints
- `GET /health` — service status
- `POST /heal` — trigger healing for specified agents (or all)
  - body:
    ```json
    {
      "agents": ["backend_specialist", "frontend_specialist"],
      "force": false,
      "retry_attempts": 2,
      "timeout_seconds": 5
    }
    ```
- Internally subscribes to Redis `approval_requests` for `CRITICAL_ALERT` to auto-heal.

## Design
- **Inputs**: Orchestrator `/system/health`, Redis channels (`approval_requests`, `healer_actions`)
- **Actions**: Ping health, publish restart intent, retry with backoff, record audit in `healer:logs`
- **Outputs**: JSON results per agent, Redis audit log

## Run
```bash
pip install fastapi uvicorn redis httpx pydantic
python agents/healer/main.py
```

## Future Enhancements
- Docker/K8s integration for real restarts
- Escalation policies (SLA, paging)
- Configurable policies per agent
