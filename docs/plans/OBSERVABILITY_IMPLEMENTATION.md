# Observability Implementation Plan & Roadmap

**Date:** 2026-02-27
**Status:** In Progress
**Objective:** Close the gap between current monitoring capabilities and the required "Full-Stack Observability" state outlined in playtest reports.

## 1. Executive Summary

The HyperStation currently lacks granular container metrics and persistent object storage monitoring. This plan outlines the steps to implement `cAdvisor` for container-level insights and `MinIO` for object storage, integrating both into the existing Prometheus/Grafana stack.

## 2. Gap Analysis

| Component | Current State | Target State | Gap |
| :--- | :--- | :--- | :--- |
| **Container Metrics** | Only basic `docker stats` available via CLI. | Real-time CPU/RAM/Network per container in Grafana. | Missing `cAdvisor`. |
| **Object Storage** | No S3-compatible storage. | Self-hosted MinIO with metrics. | Missing `MinIO` service. |
| **Dashboarding** | Basic System Health (Up/Down). | Comprehensive dashboards (Container Health, Storage I/O). | Missing Data Sources & Dashboards. |

## 3. Implementation Roadmap

### Phase 1: Infrastructure Deployment (Immediate)
- [x] **Deploy cAdvisor**: Add to `docker-compose.yml` on port `8090` (to avoid conflict).
- [x] **Deploy MinIO**: Add to `docker-compose.yml` on ports `9000` (API) / `9001` (Console).
- [x] **Configure Networking**: Ensure both services are on `backend-net`.
- [x] **Security**: Apply `no-new-privileges` and read-only volume mounts.

### Phase 2: Metric Collection (Immediate)
- [x] **Prometheus Config**: Update `prometheus.yml` to scrape:
    - `cadvisor:8080` (Internal Docker port)
    - `minio:9000` (Metrics endpoint `/minio/v2/metrics/cluster`)
- [x] **Verify Targets**: Confirm all targets are UP in Prometheus UI (`http://localhost:9090/targets`).

### Phase 3: Visualization (Next Steps)
- [x] **Import Dashboards**:
    - Docker Container Metrics (Grafana ID: 14282 or similar)
    - MinIO Overview (Grafana ID: 13502)
- [x] **Customize HyperStation**: Embed key metrics (e.g., "Total CPU Load") directly into the Next.js Dashboard via Grafana HTTP API.
- [x] **Neural Visualization**: Implemented `NeuralViz.tsx` component to visualize agent swarm connectivity.

## 4. Technical Specifications

### cAdvisor Configuration
- **Port Mapping**: `8090:8080` (Host:Container)
- **Volumes**: Read-only access to `/var/lib/docker`, `/sys`, `/var/run/docker.sock`.
- **Devices**: `/dev/kmsg` for OOM monitoring.

### MinIO Configuration
- **Storage**: Docker Volume `minio_data`.
- **Auth**: Default `minioadmin`/`minioadmin` (Change for production).
- **Metrics**: Publicly accessible for Prometheus scraping.

### Disk Usage Monitoring (Node Exporter)
To correctly visualize disk usage in Grafana (filtering out virtual filesystems), use the following PromQL query:

```promql
100 - ((node_filesystem_avail_bytes{mountpoint="/",fstype!="rootfs"} * 100) / node_filesystem_size_bytes{mountpoint="/",fstype!="rootfs"})
```

This filters for the root mountpoint and excludes virtual filesystems like `rootfs`, providing accurate disk usage for the host system.

## 5. Success Metrics
1.  **Visibility**: 100% of running containers show CPU/RAM usage in Grafana.
2.  **Storage**: MinIO bucket usage and request counts are visible.
3.  **Integration**: Prometheus successfully scrapes all 5 targets (Core, Node, cAdvisor, MinIO, Prometheus).

## 6. Risk Mitigation
- **Port Conflicts**: Mapped cAdvisor to `8090` instead of `8080`.
- **Privilege Escalation**: Removed `privileged: true` from cAdvisor, using specific capabilities/mounts instead.
- **Data Persistence**: Created named volume `minio_data` to ensure data survives restarts.
