# 🧠 Grafana Cloud Pipeline — HyperCode V2.4 Integration Guide

## What's Fixed

You now have **end-to-end observability** for HyperCode/BROski:

✅ **Metrics** (Prometheus → Grafana Cloud)
- Local Prometheus scrapes all 14 agents + infrastructure  
- Grafana Agent ships metrics to Grafana Cloud in real-time

✅ **Logs** (Docker containers → Grafana Cloud Loki)
- Agent captures container logs from `docker.sock`
- Auto-labels by container name, network, status

✅ **Traces** (OpenTelemetry → Grafana Cloud Tempo)
- OTLP receiver on `:4317` (gRPC)
- Traces pushed to Grafana Cloud with auth

## What You Need to Do

### 1. Get Grafana Cloud Credentials

Log into **Grafana Cloud** → navigate to:
```
Connections → Data sources → Prometheus → Details tab
```

Copy these values:
- **Prometheus URL** → `GRAFANA_CLOUD_PROMETHEUS_URL`
- **Org ID** → `GRAFANA_CLOUD_PROMETHEUS_USERNAME` (numeric, e.g., `123456`)
- **Loki URL** → `GRAFANA_CLOUD_LOKI_URL`
- **Loki Org ID** → `GRAFANA_CLOUD_LOKI_USERNAME` (same as Prometheus org)
- **Tempo URL** → `GRAFANA_CLOUD_TEMPO_URL`
- **Tempo Org ID** → `GRAFANA_CLOUD_TEMPO_USERNAME` (same as Prometheus org)

Then generate an **API token** with scopes:
```
metrics:write
logs:write
traces:write
```

Copy the full token → `GRAFANA_CLOUD_ACCESS_TOKEN`

### 2. Update `.env`

Edit `HyperCode-V2.4/.env` and fill in:

```bash
GRAFANA_CLOUD_PROMETHEUS_URL=https://prometheus-blocks-prod-us-central1.grafana-net.com/api/prom/push
GRAFANA_CLOUD_PROMETHEUS_USERNAME=123456           # Your org ID
GRAFANA_CLOUD_LOKI_URL=https://logs-prod-us-central1.grafana-net.com/loki/api/v1/push
GRAFANA_CLOUD_LOKI_USERNAME=123456                 # Same org ID
GRAFANA_CLOUD_TEMPO_URL=https://tempo-blocks-prod-us-central1.grafana-net.com:443/api/traces
GRAFANA_CLOUD_TEMPO_USERNAME=123456                # Same org ID
GRAFANA_CLOUD_ACCESS_TOKEN=glc_your_token_here    # Your API token
```

### 3. Start the Pipeline

#### Option A: Local dev (with local Prometheus + Agent):
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

#### Option B: Production (local Prometheus + Cloud shipper):
```bash
docker compose up --profile grafana-cloud -d
```

#### Option C: All profiles (local + agents + observability + cloud):
```bash
docker compose up --profile observability --profile grafana-cloud -d
```

### 4. Verify It's Working

**Check Prometheus locally:**
```bash
curl http://localhost:9090/api/v1/targets
```
You should see all agents + infra scraped with status ✅.

**Check Grafana Agent health:**
```bash
curl http://localhost:12345/agent/api/v1/status
```

**In Grafana Cloud:**
- Go to **Explore** → Select **Prometheus** datasource
- Query: `up` or `container_cpu_usage_seconds_total`
- You should see data flowing in (~15-30 seconds after agent startup)

## Troubleshooting

### Metrics Not Appearing
1. **Check Agent logs:**
   ```bash
   docker logs grafana-agent
   ```
   Look for `remote_write_failed` or auth errors.

2. **Verify env vars expanded:**
   ```bash
   docker inspect grafana-agent | grep GRAFANA_CLOUD
   ```
   All should be populated (not empty).

3. **Test auth manually:**
   ```bash
   curl -u <org_id>:<token> https://prometheus-blocks-prod-us-central1.grafana-net.com/api/prom/push
   ```
   Should return `204 No Content` (success) or `401` (bad token).

### Container Can't Reach Prometheus
- Agent runs in `backend-net` network. Verify Prometheus is on the same network.
- Check: `docker network inspect hypercode_public_net`

### Docker Logs Not Appearing in Loki
- Agent needs `/var/run/docker.sock` mounted (it is, check compose file).
- Verify docker daemon is accessible from inside agent:
  ```bash
  docker exec grafana-agent docker ps
  ```

## Dashboards

Once metrics are flowing, import these from Grafana Cloud:
1. **Prometheus Stats** (id `1860`) — cardinality, scrape health
2. **HyperCode Agent Metrics** (custom, built on `agent_id` labels)
3. **Docker Container Metrics** (id `893`)
4. **Celery Tasks** (custom via celery-exporter)

## Next Steps

1. ✅ **Add redis_exporter** (Redis memory, connections, keys)
2. ✅ **Add postgres_exporter** (PostgreSQL queries, connections, locks)
3. ✅ **Add alerts** in Grafana Cloud (e.g., "agent down", "high error rate")
4. ✅ **Link traces ↔ logs** in Grafana Cloud (via trace context)

---

**Questions?** Check `/monitoring/grafana-agent/agent.river` for the full config or `docker logs grafana-agent` for runtime issues.
