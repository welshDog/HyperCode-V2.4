---
name: otlp-tempo-tracing
description: HyperCode V2.4 Phase 10N OTLP distributed tracing — OpenTelemetry → Tempo → Grafana. View traces, debug missing spans, the OTLP_EXPORTER_DISABLED flag. Use when the user says "tracing", "Tempo", "OTel", "OTLP", "traces missing", "view a request flow", "Grafana traces", or "Phase 10N".
---

# otlp-tempo-tracing

OpenTelemetry tracing is LIVE since Phase 10N (April 15, 2026). FastAPI + SQLAlchemy + Redis + httpx auto-instrumented → exported via OTLP gRPC to Tempo → viewable in Grafana.

## The Pipeline

```
hypercode-core (FastAPI)
  ↓ auto-instrumented via opentelemetry-*
  ↓ OTLPSpanExporter (gRPC)
tempo:4317 (data plane)
  ↓ stored in Tempo
grafana:3001 (UI)
  ↓ Explore → Tempo datasource → search
You
```

## View Traces

1. Open `http://localhost:3001` (Grafana)
2. Click **Explore** in the left sidebar
3. Select **Tempo** as the datasource
4. Search by service name: `hypercode-core` (or any other instrumented service)
5. Or search by trace ID if you have one (X-Trace-Id header on responses)

## Confirmed-traced Endpoints

- `GET /health` → `hypercode-core`
- `GET /metrics` → `hypercode-core`
- Redis ops (`HSET`, `GET`) → `hypercode-core`
- SQLAlchemy queries (auto-instrumented)
- httpx outbound calls (auto-instrumented)

If you don't see traces from a known endpoint → check the **OTLP_EXPORTER_DISABLED** flag (next section).

## The Flag That Bit Us (real story, never re-debate)

`backend/app/core/telemetry.py` reads:

```python
OTLP_EXPORTER_DISABLED = os.environ.get("OTLP_EXPORTER_DISABLED", "false").lower() == "true"
```

**The bug we fixed:** `.env` had `OTLP_EXPORTER_DISABLED=true` with a comment "Tempo broken." Tempo was fine. The flag was wrong. Setting it to `false` (or removing it) re-enabled tracing instantly.

**Lesson:** if traces vanish, check this flag FIRST before debugging Tempo.

## Configuration

### `.env` keys

```env
OTLP_ENDPOINT=http://tempo:4317        # gRPC endpoint inside Docker network
OTLP_EXPORTER_DISABLED=false           # MUST be false (or absent) to export
OTEL_SERVICE_NAME=hypercode-core       # how it appears in Tempo search
```

### Docker Compose

`hypercode-core` and Tempo must share a network. Currently both are on `agents-net` — confirmed working. If you move services between networks, re-verify with:

```powershell
docker compose exec hypercode-core sh -c "getent hosts tempo"
# → should resolve to Tempo's IP
```

## Instrumented Packages (already pinned in `requirements.txt`)

12 OTel packages — DO NOT remove without checking what breaks:

```
opentelemetry-api
opentelemetry-sdk
opentelemetry-exporter-otlp-proto-grpc
opentelemetry-instrumentation-fastapi
opentelemetry-instrumentation-sqlalchemy
opentelemetry-instrumentation-redis
opentelemetry-instrumentation-httpx
opentelemetry-instrumentation-logging
opentelemetry-instrumentation-asgi
opentelemetry-instrumentation-wsgi
opentelemetry-semantic-conventions
opentelemetry-util-http
```

## Add Manual Spans (for non-auto-instrumented code)

```python
from opentelemetry import trace
tracer = trace.get_tracer(__name__)

def expensive_thing(x):
    with tracer.start_as_current_span("expensive_thing") as span:
        span.set_attribute("input.x", x)
        # ... work ...
        span.set_attribute("result.size", len(result))
        return result
```

The span automatically becomes a child of the current request's trace — no propagation needed if called from a FastAPI handler.

## Common Failures

| Symptom | Likely cause | Fix |
|---|---|---|
| No traces in Grafana | `OTLP_EXPORTER_DISABLED=true` | Set to `false` or remove the var |
| `Failed to connect to tempo:4317` | Network mismatch | Confirm `hypercode-core` + `tempo` both on `agents-net` |
| Traces appear but spans missing | Instrumentation not initialized | Check `telemetry.py` is imported early in startup |
| Tempo shows traces but Grafana panel blank | Datasource misconfigured | Grafana → Datasources → Tempo → URL = `http://tempo:3200` |
| Trace ID in response header but no trace in Tempo | Sampler dropped it | Check sampling config (`OTEL_TRACES_SAMPLER` env var) |
| High latency on requests after enabling | OTel overhead | Tune sampling — e.g. `parentbased_traceidratio=0.1` for 10% sampling |

## Debugging Workflow

When a request looks slow:

1. Make the request, copy the `X-Trace-Id` from response headers
2. Grafana → Explore → Tempo → search by trace ID
3. See the full waterfall: which span took the time?
4. Drill into the slow span — its attributes tell you what it was doing
5. Cross-reference with logs (Loki) using the same trace ID — `traceID=<id>` filter

## Companion Skills

- `phase-10-tracker` — Phase 10N context
- `docker-stack-ops` — Tempo container ops
- `stripe-webhook-handler` — trace a checkout request end-to-end via Tempo

## Hard Rules

- **`OTLP_EXPORTER_DISABLED=false`** — keep this in production. Disable only for short isolated debug sessions.
- **Tempo and Grafana stay on `obs-net`** (`internal: true`) — never expose to internet
- **Service name `hypercode-core`** is the canonical identifier in Tempo. Don't rename without updating dashboards.
- **Don't remove OTel packages** from `requirements.txt` — they're load-bearing
