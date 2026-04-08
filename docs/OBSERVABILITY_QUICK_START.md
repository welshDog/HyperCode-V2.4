# HyperCode Observability & Life Plans - Quick Start 🚀

## What You Just Built

**3 core components:**

1. **Test Suite** (`tests/test_agent_observability.py`)
   - Unit tests: Health checks, SLO baselines
   - Chaos tests: Failure injection, recovery
   - Stress tests: 100 req/sec load, memory leaks
   - Soak tests: 72-hour endurance
   - Red-team tests: Prompt injection, resource exhaustion

2. **Life Plans** (`agents/life-plans/`)
   - YAML runbooks for each agent
   - SLOs, failure modes, recovery steps
   - Dependency graphs, metrics to monitor
   - On-call playbooks, migration paths
   - **Examples:** hypercode-core.yaml, crew-orchestrator.yaml

3. **Observability Stack** (already in docker-compose.yml)
   - Prometheus (metrics scraping)
   - Loki (log aggregation)
   - Tempo (distributed tracing)
   - Grafana (dashboards & alerts)

---

## Getting Started (5 minutes)

### Step 1: Start the Observability Stack

```bash
cd HyperCode-V2.0

# Spin up Prometheus, Loki, Grafana, Tempo
make -f Makefile.observability observability-stack

# Or manually:
docker-compose up -d prometheus loki tempo grafana promtail node-exporter cadvisor
```

**Verify:**
```bash
make -f Makefile.observability dev-health-check
```

Output:
```
HyperCode Core:     ok
Crew Orchestrator:  ok
Prometheus:         ok
Grafana:            ok
```

### Step 2: Start Your Agents

```bash
# Start all services with agent profiles
docker-compose up -d --profile agents --profile mission
```

**Verify agents are running:**
```bash
docker-compose ps | grep -E "hypercode-core|crew-orchestrator|redis|postgres"
```

### Step 3: Access Grafana

```
http://localhost:3001
Username: admin
Password: admin
```

You'll see:
- Dashboards (if provisioned)
- Prometheus as data source
- Loki for logs
- Tempo for traces

### Step 4: Run Tests

```bash
# Install test dependencies
pip install pytest requests docker

# Run unit tests (5 min)
make -f Makefile.observability test-unit

# Run chaos tests (10 min)
make -f Makefile.observability test-chaos

# Run all tests except soak (20 min)
make -f Makefile.observability test
```

### Step 5: View Life Plans

```bash
# See the template
cat agents/life-plans/TEMPLATE.md

# View examples
cat agents/life-plans/hypercode-core.yaml
cat agents/life-plans/crew-orchestrator.yaml
```

---

## Understanding the Test Results

### Unit Tests Example Output

```
test_services_health PASSED                              [  5%]
✓ hypercode-core: 45.3ms
✓ crew-orchestrator: 32.1ms
test_prometheus_scrape_targets PASSED                    [ 10%]
✓ Prometheus scraping 8 targets
test_loki_log_ingestion PASSED                           [ 15%]
✓ Loki ingesting logs from 5 streams
```

**What it means:**
- ✓ All services responding within SLO (<500ms for /health)
- ✓ Prometheus is collecting metrics from all agents
- ✓ Logs are flowing into Loki

### Chaos Tests Example Output

```
test_redis_failure_recovery PASSED                       [ 40%]
🔴 Killing Redis...
✓ Core degraded gracefully (expected)
⏳ Waiting 30s for Redis restart...
✓ Redis auto-recovered
```

**What it means:**
- ✓ When Redis fails, Core detects it and degrades (no crash)
- ✓ Healer automatically restarts Redis
- ✓ System recovers without manual intervention

### Stress Tests Example Output

```
test_concurrent_load_100_req_sec PASSED                  [ 60%]
✓ Load test: 5934 requests, 99.2% success, p99=287.3ms
```

**What it means:**
- ✓ System handled 100 req/sec sustained
- ✓ >95% succeeded (SLO met)
- ✓ Latency p99 stayed under 500ms (SLO)

---

## Monitoring in Grafana

### Access Dashboards

1. **Go to:** http://localhost:3001
2. **Click:** Home → Dashboards
3. **Look for:**
   - `HyperCode Core` — Latency, errors, memory
   - `Crew Orchestrator` — Task completion, agent health
   - `Container Metrics` — CPU, memory per service
   - `Redis` — Connection counts, memory usage
   - `PostgreSQL` — Query latency, connections

### Common Queries

**Latency (p95, p99):**
```
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{job="hypercode-core"}[5m]))
```

**Error rate:**
```
rate(http_requests_total{job="hypercode-core",status=~"5.."}[5m])
```

**Memory usage:**
```
container_memory_usage_bytes{name="hypercode-core"} / 1024 / 1024
```

**Task success rate (Crew):**
```
rate(tasks_completed_total{status="success"}[5m]) / rate(tasks_completed_total[5m])
```

---

## Creating Life Plans for Other Agents

### Template Structure

```yaml
service_identity:
  name: "my-agent"
  codename: "🤖 My Cool Agent"
  version: "2.0.0"
  core_purpose: "What this agent does"

responsibility_matrix:
  primary_role: "EXECUTOR"
  owns:
    - "Feature X"
  critical_dependencies:
    - redis:6379
    - postgres:5432

performance_slos:
  latency_p99_ms: 500
  error_rate_max: 0.01
  availability_percent: 99.9

failure_modes:
  - mode_id: "redis_down"
    description: "Redis unavailable"
    symptoms: ["..."]
    recovery_steps: ["1. ...", "2. ..."]
    expected_mttr_minutes: 2
    user_impact: "DEGRADED"
    sev: "P2"

metrics_to_monitor:
  - name: "request_latency"
    prometheus_query: "..."
    alert_if: "..."
```

### Steps to Create One

```bash
# 1. Copy template
cp agents/life-plans/hypercode-core.yaml agents/life-plans/my-agent.yaml

# 2. Edit with your agent's details
vim agents/life-plans/my-agent.yaml

# 3. Commit
git add agents/life-plans/my-agent.yaml
git commit -m "docs: add life plan for my-agent"
```

---

## Running Long Soak Tests

### 72-Hour Test (Real Production Validation)

```bash
# Takes 72 hours!
make -f Makefile.observability test-soak

# Or manually:
python3 tests/run_tests.py --suite soak --soak-hours 72
```

**While it runs:**
- Check Grafana dashboards in real-time
- Watch for memory leaks (should be flat)
- Verify error rate stays <1%
- Monitor uptime percentage

**After it completes:**
- Results saved to `/tmp/soak_test_metrics.json`
- Can plot memory/CPU/latency trends
- Use for capacity planning

### Quick Soak (1 hour for testing)

```bash
make -f Makefile.observability test-soak-quick
```

---

## Integrating with CI/CD

### GitHub Actions Example

```yaml
name: Observability Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Start observability stack
        run: docker-compose up -d prometheus loki grafana
      
      - name: Install dependencies
        run: pip install pytest requests docker
      
      - name: Run unit tests
        run: make -f Makefile.observability test-unit
      
      - name: Run chaos tests
        run: make -f Makefile.observability test-chaos
      
      - name: Upload metrics
        if: always()
        uses: actions/upload-artifact@v2
        with:
          name: soak-metrics
          path: /tmp/soak_test_metrics.json
```

---

## On-Call Playbooks

When an alert fires in Grafana:

1. **Read the alert name:** `HypercodeCore_HighErrorRate`
2. **Find in life-plan:** `agents/life-plans/hypercode-core.yaml`
3. **Look up failure mode:** Search for "high_error_rate"
4. **Follow recovery steps:**
   - Check logs in Loki
   - Verify dependencies (Redis, Postgres)
   - If recent deploy, rollback
   - If not, investigate

---

## Quick Reference: Make Commands

```bash
# Stack management
make -f Makefile.observability observability-stack    # Start stack
make -f Makefile.observability restart                # Restart services
make -f Makefile.observability clean                  # Destroy all

# Tests
make -f Makefile.observability test-unit              # Unit tests (5 min)
make -f Makefile.observability test-chaos             # Chaos tests (10 min)
make -f Makefile.observability test-stress            # Stress tests (10 min)
make -f Makefile.observability test                   # All tests (20 min)
make -f Makefile.observability test-soak-quick        # 1-hour soak

# Debugging
make -f Makefile.observability dev-health-check       # Check all services
make -f Makefile.observability logs                   # Tail logs
make -f Makefile.observability metrics                # Show Prometheus queries
make -f Makefile.observability dev-watch-logs         # Real-time log stream

# Documentation
make -f Makefile.observability life-plans             # View life-plan guide
make -f Makefile.observability docs                   # View all docs
```

---

## Next Steps

1. ✅ **Start the stack** (observability-stack)
2. ✅ **Run unit tests** (test-unit)
3. ✅ **Create life-plans** for your other agents
4. ✅ **Set up Grafana dashboards** for each agent
5. ✅ **Run chaos tests** in staging (test-chaos)
6. ✅ **Schedule soak tests** in CI/CD
7. ✅ **Integrate on-call playbooks** with your alerting system

---

## Support & Questions

- **Life Plans Guide:** `agents/life-plans/TEMPLATE.md`
- **Test Examples:** `tests/test_agent_observability.py`
- **Monitoring Docs:** `monitoring/` folder
- **Grafana Dashboards:** http://localhost:3001

---

## Key Metrics to Track

| Service | Metric | SLO | Alert |
|---------|--------|-----|-------|
| HyperCode Core | Latency p99 | <500ms | >500ms for 5m |
| HyperCode Core | Error rate | <1% | >1% for 5m |
| Crew Orchestrator | Task success | >95% | <95% for 5m |
| All Services | Memory | <80% of limit | >80% for 10m |
| Redis | Connectivity | Online | Offline for 1m |
| PostgreSQL | Connectivity | Online | Offline for 1m |

---

Good luck! You're now running a future-ready, observable, resilient agent system. 🚀
