## The HyperCode Master Dashboard Import Guide

Based on everything we've explored across your Grafana Cloud instance (ML App, Adaptive Telemetry, existing dashboards, and the marketplace), here's your definitive list of the best dashboards to import, tailored to your stack (Python FastAPI, Docker, Loki, Prometheus, AI agents).

***

### Your Dashboard Import Cheat Sheet

Navigate to: **hypercode.grafana.net → Dashboards → New → Import**

***

### TIER 1 — Must-Have (Import These First)

#### 1. Node Exporter Full — ID: `1860` [grafana](https://grafana.com/grafana/dashboards/1860-node-exporter-full/)
- **Datasource:** Prometheus
- **What it shows:** CPU, RAM, disk I/O, network per host — full Linux server vitals
- **Why HyperCode needs it:** Your Docker host machine health — the foundation of everything
- **Prereq:** `node_exporter` running as a container or systemd service

```yaml
# docker-compose addition
node-exporter:
  image: prom/node-exporter:latest
  ports: ["9100:9100"]
  volumes:
    - /proc:/host/proc:ro
    - /sys:/host/sys:ro
```

***

#### 2. FastAPI Observability — ID: `16110` [grafana](https://grafana.com/grafana/dashboards/19908-docker-container-monitoring-with-prometheus-and-cadvisor/)
- **Datasource:** Loki + Prometheus
- **What it shows:** Request counts, error rates, avg duration per endpoint, P95/P99 latency, live log tail
- **Why HyperCode needs it:** Every BROski Agent API call, every `/invoke`, every health check — all visible
- **Prereq:**
```bash
pip install prometheus-fastapi-instrumentator
```
```python
# In your FastAPI main.py
from prometheus_fastapi_instrumentator import Instrumentator
Instrumentator().instrument(app).expose(app)
```

***

#### 3. cAdvisor Docker Insights — ID: `19908` [grafana](https://grafana.com/grafana/dashboards/19908-docker-container-monitoring-with-prometheus-and-cadvisor/)
- **Datasource:** Prometheus
- **What it shows:** Per-container CPU %, memory usage, network I/O, restart counts — live
- **Why HyperCode needs it:** See exactly which AI agent container is eating RAM or spiking CPU
- **Prereq:**
```yaml
cadvisor:
  image: gcr.io/cadvisor/cadvisor:latest
  ports: ["8080:8080"]
  volumes:
    - /:/rootfs:ro
    - /var/run:/var/run:ro
    - /sys:/sys:ro
    - /var/lib/docker/:/var/lib/docker:ro
```

***

#### 4. Loki Dashboard — ID: `15315` [grafana](https://grafana.com/grafana/dashboards/15315-loki-dashboard/)
- **Datasource:** Loki + Prometheus
- **What it shows:** Timeline of log volume + full searchable log stream with quick-filter bar
- **Why HyperCode needs it:** Grep across ALL your agent logs in one place, with timeline correlation
- **Prereq:** Promtail or Alloy already shipping logs to Loki (already in your stack)

***

### TIER 2 — High Value Add-Ons

#### 5. Loki Logs with Quicksearch — ID: `13359` [grafana](https://grafana.com/grafana/dashboards/13359-logs/)
- **Datasource:** Loki
- **What it shows:** Ultra-simple — filter by container name + case-insensitive search
- **Best for:** Quick daily debugging — just type "broski" or "error" and see everything instantly

#### 6. Loki Dashboard Quick Search — ID: `12019` [grafana](https://grafana.com/grafana/dashboards/12019-loki-dashboard-quick-search/)
- **Datasource:** Loki + Prometheus
- **What it shows:** Timeline bars + log panel with namespace/pod/container filters
- **Best for:** When you have many containers and want to isolate by service name fast

***

### How to Import (Step-by-Step)

```
1. Go to https://hypercode.grafana.net
2. Left sidebar → Dashboards → click blue "New" button → "Import"
3. In the "Import via grafana.com" box → type the ID number → click "Load"
4. On the next screen → set the Datasource dropdown to your Prometheus or Loki source
5. Click "Import" — done, it appears instantly
```

***

### The Full Stack Picture — What Each Dashboard Monitors

```
Your Stack Layer          →  Dashboard to Use
─────────────────────────────────────────────
Linux Host (CPU/RAM/Disk) →  Node Exporter Full (1860)
Docker Containers         →  cAdvisor Docker Insights (19908)
FastAPI / BROski APIs     →  FastAPI Observability (16110)
All Log Streams           →  Loki Dashboard (15315)
Quick Log Debug           →  Loki Quicksearch (13359)
```

***

### Prerequisites Wiring Checklist

Before the dashboards show data, confirm these are in your `docker-compose.yml` and `prometheus.yml`:

**prometheus.yml scrape targets:**
```yaml
scrape_configs:
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']
  
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']
  
  - job_name: 'fastapi-app'
    static_configs:
      - targets: ['your-app:8000']  # where /metrics is exposed
```

Once these three scrapers are live and the dashboards imported, your hypercode.grafana.net will go from empty panels to a full production-grade observability command centre — CPU, memory, per-container stats, per-endpoint API performance, and searchable logs all in one place.
