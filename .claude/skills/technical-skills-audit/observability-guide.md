# 📊 Observability — Prometheus + Grafana

## Stack Overview

| Component | Port | Purpose |
|---|---|---|
| Prometheus | 9090 | Metrics scraping & storage |
| Grafana | 3001 | Dashboards & alerting |
| Node Exporter | 9100 | Host system metrics |
| cAdvisor | 8090 | Container metrics |

## Start Observability Stack

```bash
# Local stack
docker compose -f docker-compose.monitoring.yml up -d

# With Grafana Cloud
docker compose -f docker-compose.grafana-cloud.yml up -d

# Via Makefile
make -f Makefile.observability start
```

## Key Prometheus Metrics

```promql
# Agent health
hypercode_agent_health_status{agent="healer"}

# Service restart count
hypercode_service_restarts_total

# API response time (p95)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Redis memory usage
redis_memory_used_bytes

# Active tasks in queue
hypercode_active_tasks_total
```

## Grafana Alert Rules

Suggest alerting on:
- Any agent health = 0 (down) → trigger Healer Agent
- Service restarts > 3 in 5min → PagerDuty / Discord notification
- Redis memory > 80% → scale warning
- API p95 latency > 2s → performance alert

## Config Files

- `prometheus.yml` — scrape targets & rules
- `grafana/` — dashboard JSON exports
- `grafana/grafana_quotas.ini` — Grafana org quotas (moved from root)
- `monitoring/` — alert rules & recording rules
