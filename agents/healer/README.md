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

## Restart policy and host-load guard (MAPE-K engine)

`mape_k_engine.py` restarts a service only after **3 consecutive** bad probes, verifies the restart by polling for the
service's `startup_grace_seconds` (core 240 s), and logs through the `mape_k` logger at INFO (JSON, like the rest of the
healer's output). On top of that, a **host-load guard** holds docker/http restarts while the VM itself is starved, because
probe failures during a spike are usually the load and a restart under load makes it worse. Alert-only actions are never
held. The guard fails open (unreadable `/proc` = nothing held) and restarts a held service anyway after
`HEALER_LOAD_GUARD_MAX_HOLD_SECONDS`, so a real outage under sustained load still gets fixed. Look for `[GUARD]` lines.

| Env var | Default | Meaning |
|---|---|---|
| `HEALER_RESTART_MIN_CONSECUTIVE` | 3 | consecutive bad probes before a restart |
| `HEALER_VERIFY_POLL_SECONDS` | 5 | poll interval while verifying a restart |
| `HEALER_RESET_AFTER_HEALTHY` | 6 | healthy probes that clear the failed-heal counter / backoff |
| `HEALER_LOAD_GUARD_ENABLED` | true | master switch for the guard |
| `HEALER_LOAD_GUARD_CPU_PRESSURE` | 50 | hold when `/proc/pressure/cpu` "some" avg10 is at or above this percent |
| `HEALER_LOAD_GUARD_LOAD_PER_CPU` | 2.0 | hold when 1-min loadavg / CPUs is at or above this |
| `HEALER_LOAD_GUARD_MIN_MEM_MB` | 0 (off) | hold when MemAvailable is below this many MB |
| `HEALER_LOAD_GUARD_SYSTEMIC_MIN` | 2 | hold when this many services that were healthy in the last `..._RECENT_HEALTHY_SECONDS` (300) went unhealthy together (<2 = off) |
| `HEALER_LOAD_GUARD_MAX_HOLD_SECONDS` | 600 | restart anyway after holding this long |
| `HEALER_LOG_LEVEL` | INFO | level for the `mape_k` logger |
| `HEALER_ALERT_REPEAT_SECONDS` | 3600 | alert-only services (`critical=False`, e.g. the stopped observability stack) alert once per outage, then at most this often; 0 = every cooldown cycle (old behaviour). A `[ALERT] X recovered` line follows when they come back |

The healer container sees VM-wide numbers (`/proc/loadavg`, `/proc/pressure/cpu`, `/proc/meminfo` are not namespaced).
Tests: `agents/healer/tests/test_mape_k_policy.py` (run in CI by `healer-policy-tests.yml`).

