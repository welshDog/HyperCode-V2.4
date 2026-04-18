---
name: hypercode-grafana
description: Build and manage Grafana dashboards, datasources, and alerts for HyperCode V2.4. Use when creating new dashboards, adding Prometheus panels, wiring Loki log queries, correlating Tempo traces, or setting up AlertManager webhooks. Also covers the Mission Control dashboard build.
---

# HyperCode Grafana Skill

## Stack
- Grafana at `http://localhost:3001`
- Prometheus at `http://localhost:9090` (7/7 targets UP)
- Loki at `http://localhost:3100` (logs)
- Tempo at `http://localhost:3200` (traces)
- AlertManager at `http://localhost:9093`

## Key Files
```
monitoring/grafana/grafana.ini              ← main config
monitoring/grafana/dashboards/             ← JSON dashboard files
monitoring/grafana/provisioning/           ← auto-provisioning
monitoring/grafana/provisioning/datasources/ ← datasource configs
monitoring/prometheus/prometheus.yml       ← scrape targets (LIVE config)
monitoring/alertmanager/alertmanager.yml   ← alert routing
monitoring/rules/                          ← Prometheus alert rules
```

## Dashboard JSON Template

```json
{
  "title": "HyperCode Mission Control",
  "uid": "hypercode-mission-control",
  "tags": ["hypercode", "production"],
  "timezone": "browser",
  "refresh": "10s",
  "panels": []
}
```

Save to: `monitoring/grafana/dashboards/hypercode-mission-control.json`

## Useful Prometheus Queries

```promql
# Container health — all up?
up{job=~"hypercode.*"}

# Request rate on core API
rate(http_requests_total{service="hypercode-core"}[5m])

# Error rate
rate(http_requests_total{service="hypercode-core",status=~"5.."}[5m])
  / rate(http_requests_total{service="hypercode-core"}[5m])

# Memory usage per container
container_memory_usage_bytes{name=~"hypercode.*"} / 1024 / 1024

# Redis operations
rate(redis_commands_processed_total[5m])

# Agent heartbeat (custom metric)
hypercode_agent_heartbeat_seconds
```

## Loki Log Queries

```logql
# All errors across services
{job="hypercode"} |= "ERROR"

# Stripe webhook events
{service="hypercode-core"} |= "stripe" |= "webhook"

# Agent crashes
{job="hypercode-agents"} |= "exit" or |= "OOM" or |= "killed"

# BROski$ awards
{service="hypercode-core"} |= "award_tokens"
```

## Datasource Linking (Distributed Tracing Correlation)

```yaml
# provisioning/datasources/all.yml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    url: http://prometheus:9090
    jsonData:
      exemplarTraceIdDestinations:
        - name: trace_id
          datasourceUid: tempo

  - name: Loki
    type: loki
    url: http://loki:3100
    jsonData:
      derivedFields:
        - name: trace_id
          matcherRegex: '"trace_id":"(\w+)"'
          url: '$${__value.raw}'
          datasourceUid: tempo

  - name: Tempo
    type: tempo
    url: http://tempo:3200
    jsonData:
      tracesToLogs:
        datasourceUid: loki
        tags: ['service']
```

## Alert Rules

```yaml
# monitoring/rules/hypercode.yml
groups:
  - name: hypercode
    rules:
      - alert: ContainerDown
        expr: up{job=~"hypercode.*"} == 0
        for: 30s
        labels:
          severity: critical
        annotations:
          summary: "Container {{ $labels.instance }} is down"

      - alert: HighErrorRate
        expr: |
          rate(http_requests_total{status=~"5.."}[5m]) 
          / rate(http_requests_total[5m]) > 0.01
        for: 2m
        labels:
          severity: warning

      - alert: HighMemoryUsage
        expr: |
          container_memory_usage_bytes{name="hypercode-core"} 
          / 1024 / 1024 > 1200
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "hypercode-core memory > 1.2GB (limit 1.5GB)"
```

## Discord Webhook Alert (AlertManager)

```yaml
# alertmanager.yml — add receiver
receivers:
  - name: discord
    webhook_configs:
      - url: 'http://broski-bot:8100/alert-webhook'
        send_resolved: true
```

## Mission Control Dashboard — Panel Checklist

Build these panels in order:
- [ ] Stat: containers healthy (29/29)
- [ ] Stat: Prometheus targets UP
- [ ] Time series: request rate (core API)
- [ ] Time series: error rate
- [ ] Gauge: memory usage (core, postgres, redis)
- [ ] Table: agent heartbeats (name, status, last seen)
- [ ] Logs panel: live ERROR stream (Loki)
- [ ] Stat: BROski$ awarded today
- [ ] Stat: active WebSocket connections
