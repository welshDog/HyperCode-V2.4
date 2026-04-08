# Hyper-Mission System Monitoring Setup Guide

## Overview
This document details the complete monitoring stack implementation for the Hyper environment, utilizing Prometheus for metrics collection and Grafana for visualization.

## Architecture
- **Prometheus**: Time-series database scraping metrics from all services.
  - **Retention**: 15 days.
  - **Storage**: Persistent volume `prometheus_data`.
  - **Scrape Interval**: 15s.
- **Grafana**: Visualization platform.
  - **Auth**: Admin password configured via `GF_SECURITY_ADMIN_PASSWORD`.
  - **Provisioning**: Dashboards and datasources auto-loaded.
- **Exporters**:
  - `node-exporter`: Host system metrics (CPU, Mem, Disk).
  - `cadvisor`: Docker container metrics.
  - `prom-client`: Application-level business metrics (Express.js).
- **Alerting**: `alertmanager` handling critical thresholds.

## Configuration Files

### 1. Prometheus (`prometheus.yml`)
Configures scrape jobs for:
- `node_app` (API replicas via DNS discovery)
- `node_exporter`
- `cadvisor`
- `prometheus` (self)
- `alertmanager`

### 2. Alerting Rules (`alert.rules.yml`)
Defines critical alerts:
- **HighCpuUsage**: > 80% for 5m.
- **HighMemoryUsage**: > 85% for 5m.
- **InstanceDown**: Any target down for 1m.
- **HighErrorRate**: API error rate > 5%.
- **SlowResponseTime**: API response > 1s.

### 3. Alertmanager (`alertmanager.yml`)
Routes alerts to configured receivers (currently a placeholder webhook).

## Dashboards
1.  **Node.js Application Dashboard**: Application throughput, latency, and business metrics.
2.  **System Dashboard**: Host-level resource usage.

## Deployment
The monitoring stack is integrated into `docker-compose.prod.yml`.

### Start Monitoring
```bash
docker-compose -f docker-compose.prod.yml up -d prometheus grafana alertmanager node-exporter cadvisor
```

### Access Points
- **Grafana**: `http://localhost:3003` (User: `admin`, Pass: `admin`)
- **Prometheus**: `http://localhost:9092`
- **Alertmanager**: `http://localhost:9093`

## Troubleshooting
- **Missing Metrics**: Check target status at `http://localhost:9092/targets`.
- **Alerts not firing**: Verify `alertmanager` logs.
- **Grafana Login Fail**: Check `GF_SECURITY_ADMIN_PASSWORD` in `docker-compose.prod.yml`.
