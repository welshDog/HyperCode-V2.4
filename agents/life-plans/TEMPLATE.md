# Agent Life Plan Template v2.0.0

A structured service runbook for every HyperCode agent. Combines identity, dependencies, SLOs, failure modes, and evolution roadmap in a single source of truth.

## Template Structure

```yaml
# agents/life-plans/[AGENT_NAME].yaml

service_identity:
  name: "agent-name"
  codename: "Human-readable alias"
  version: "2.0.0"
  core_purpose: |
    What this agent does. 1-3 sentences.
  
  contact:
    owner: "Lyndz"
    slack: "#hyper-agents"
    runbook: "https://wiki.internal/agent-name"

responsibility_matrix:
  primary_role: "EXECUTOR | ARCHITECT | OBSERVER | COMMUNICATOR | VALIDATOR"
  owns:
    - "Feature/system/domain"
    - "Another domain"
  depends_on:
    - "redis:6379 → Task queue"
    - "postgres:5432 → Session state"
    - "crew-orchestrator:8080 → Task dispatch"
  dependents:
    - "devops-agent (receives deploy commands)"
    - "test-agent (receives validation tasks)"

communication_contract:
  input_endpoints:
    - "GET /health → 200 {status: ok, uptime_seconds: X}"
    - "GET /metrics → 200 (Prometheus format)"
    - "POST /chat → 200 {response: ..., latency_ms: X}"
    - "POST /execute → 200 {task_id, status}"
  
  output_events:
    - "redis://${AGENT_NAME}-queue → Task results"
    - "postgres:events_${AGENT_NAME} → Audit log"

performance_slos:
  latency_p99_ms: 500
  latency_p95_ms: 300
  error_rate_max: 0.01  # 1%
  availability: 0.999   # 99.9% uptime
  memory_limit_mb: 512
  cpu_limit_cores: "0.5"

failure_modes:
  - mode: "redis_unavailable"
    symptoms: "POST /chat returns 503, logs contain 'Redis connection refused'"
    recovery: "Auto-reconnect every 1s. Degrade to in-memory cache. Healer restarts Redis."
    mttr_minutes: 2
    impact: "DEGRADED (slower, cached responses)"
  
  - mode: "postgres_unavailable"
    symptoms: "GET /health returns 503, database pool exhausted"
    recovery: "Fail-safe to sessionless mode. Wait for Postgres. Manual intervention if >10min"
    mttr_minutes: 5
    impact: "CRITICAL (session history lost)"
  
  - mode: "memory_leak"
    symptoms: "Memory grows >50% over 24h, container killed by OOM"
    recovery: "Monitor via Prometheus container_memory_usage_bytes. Alert at 80%. Restart at 90%."
    mttr_minutes: 1
    impact: "SEVERE (cascading failure to dependents)"
  
  - mode: "hanging_request"
    symptoms: "POST /chat requests timeout after 30s, thread pool exhausted"
    recovery: "Timeout at 5s. Circuit breaker trips. Manual investigation."
    mttr_minutes: 15
    impact: "CRITICAL (all users affected)"

metrics_to_monitor:
  - metric: "http_request_duration_seconds"
    labels: "{job='agent-name'}"
    alert_if: "histogram_quantile(0.99, ...) > 0.5"
  
  - metric: "http_requests_total"
    labels: "{job='agent-name', status=~'5..'}"
    alert_if: "rate(...[5m]) > 0.01"
  
  - metric: "container_memory_usage_bytes"
    labels: "{name='agent-name'}"
    alert_if: "(...) > 450 * 1024 * 1024"  # 450MB threshold
  
  - metric: "process_resident_memory_bytes"
    alert_if: "Growth >50% month-over-month"

deployment:
  image_registry: "ghcr.io/welshdog"
  image_name: "agent-name"
  image_tag: "latest"
  
  docker_compose_service: "agent-name"
  container_port: "8XXX"
  exposed_port: "8XXX (internal), 127.0.0.1:8XXX (if external)"
  
  healthcheck:
    endpoint: "GET /health"
    interval_seconds: 30
    timeout_seconds: 10
    retries: 3
    start_period_seconds: 30
  
  restart_policy: "unless-stopped"
  resource_limits:
    cpus: "0.5"
    memory: "512M"
  resource_reservations:
    cpus: "0.1"
    memory: "256M"

logging:
  driver: "json-file"
  format: "JSON"
  retention:
    max_size: "10m"
    max_file: "3"
  fields:
    - "timestamp"
    - "level"
    - "service"
    - "request_id"
    - "user_id (redacted in storage)"
    - "latency_ms"
    - "status_code"

versioning:
  current: "2.0.0"
  breaking_changes_v2_1_0:
    - "Endpoint changed /execute → /task"
    - "Redis key format changed task: → task_v2:"
  migration_v2_0_to_v2_1:
    - "1. Deploy v2.1.0 alongside v2.0.0"
    - "2. Run migration script: `redis-cli KEYS 'task:*' | xargs ...`"
    - "3. Cutover: Update docker-compose.yml to v2.1.0"
    - "4. Rollback window: 24 hours"
  
  deprecation_schedule:
    v2_0: "Supported until 2026-06-01"
    v1_9: "EOL 2026-01-01"

evolution_roadmap:
  v2_0: "Stable MVP, Redis + PostgreSQL backend"
  v2_1: "Streaming responses, WebSocket support"
  v2_2: "LLM-swap interface (OpenAI-compatible /v1/chat)"
  v3_0: "Kubernetes-native, horizontal scaling"

integration_checklist:
  - "[ ] Service starts without errors"
  - "[ ] /health endpoint responds <100ms"
  - "[ ] Prometheus /metrics exported"
  - "[ ] Logs shipped to Loki"
  - "[ ] Traces (if applicable) in Tempo"
  - "[ ] SLOs defined and monitored"
  - "[ ] Runbook written"
  - "[ ] On-call rotation documented"

on_call_escalation:
  tier_1: "Watch Grafana alerts, restart via Healer if needed"
  tier_2: "Check logs in Grafana Loki, investigate root cause"
  tier_3: "Debug traces in Grafana Tempo, coordinate with dependent teams"
  tier_4: "Incident commander, post-mortem"
```

---

## How to Use

### For Operators (Running the System)

1. **Check SLOs during incident:**
   ```bash
   cat agents/life-plans/agent-name.yaml | grep -A 5 "performance_slos"
   ```

2. **Understand failure modes:**
   ```bash
   # If /health returns 503
   grep -A 3 "redis_unavailable" agents/life-plans/agent-name.yaml
   ```

3. **Monitor metrics:**
   - Open Grafana (http://localhost:3001)
   - Search dashboard for agent name
   - Verify latency_p99 < SLO

### For Developers

1. **Before committing a change:**
   - Update version in life-plan YAML
   - Add to `breaking_changes` or `migration` if needed
   - Update metrics list if you added instrumentation

2. **When adding a new service dependency:**
   - Add to `depends_on:`
   - Add failure mode in `failure_modes:`
   - Add alert rule in `metrics_to_monitor:`

3. **Updating after incident:**
   - Document what happened in failure_modes
   - Add alert threshold that would catch it next time

### For On-Call

1. **Alert triggered:**
   - Read: service_identity.codename, core_purpose
   - Read: failure_modes (match symptoms to mode)
   - Execute recovery steps
   - If MTTR > 5min, escalate to Tier 3

2. **Post-incident:**
   - Was the metric threshold correct? Update it.
   - Was MTTR accurate? Update it.
   - Commit back to repo.

---

## Integration with Observability Stack

### Prometheus Scrape Config (auto-generated from life-plan)

```yaml
scrape_configs:
  - job_name: "agent-name"
    metrics_path: /metrics
    static_configs:
      - targets: ["agent-name:8XXX"]
    # Derived from: service_identity.name + communication_contract.input_endpoints
```

### Grafana Dashboard (auto-generated)

- Panel 1: Latency (p50, p95, p99)
- Panel 2: Error rate
- Panel 3: Memory usage with threshold overlay
- Panel 4: Request volume
- Panel 5: Dependency status (linked services)

### Loki Query (auto-generated)

```logql
{service="agent-name"} | json | status_code >= 500
```

### Alert Rules (auto-generated)

```yaml
- alert: AgentNameHighErrorRate
  expr: rate(http_requests_total{job="agent-name",status=~"5.."}[5m]) > 0.01
  for: 5m
  annotations:
    summary: "agent-name error rate {{ $value | humanizePercentage }}"
    runbook: "https://wiki.internal/agent-name"
```

---

## Benefits

✅ **Single source of truth** — No docs scattered across wikis  
✅ **Machine-readable** — Tools can auto-generate dashboards, alerts, configs  
✅ **Human-readable** — Ops can understand failure modes without code  
✅ **Versionable** — Git history of every change to SLOs, dependencies  
✅ **Actionable** — Includes MTTR, recovery steps, escalation paths  
✅ **Tied to reality** — Backed by Prometheus, Loki, actual metrics

---

## Next Steps

1. Create `agents/life-plans/` folder
2. Copy this template 12 times (one per agent)
3. Fill in agent-specific values
4. Commit to Git
5. Wire into Grafana provisioning (auto-dashboard generation)
6. Add to on-call runbook
