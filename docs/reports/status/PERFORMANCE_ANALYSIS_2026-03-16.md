# HyperCode V2.0 — Performance Analysis & Load Root Cause Report (2026-03-16)

## Executive Summary

Current system load is primarily driven by **internal observability + tooling overhead under tight Docker Desktop resource constraints**, not by legitimate traffic spikes.

Root causes identified:
- **Memory pressure** on the host/Docker Desktop VM (available memory observed as low as ~530–760 MB), triggering downstream instability.
- **cAdvisor** is consuming **~1.38 GiB RAM** and frequently **~10–40% CPU**, dominating the resource budget.
- **MCP stdio tool containers** (`mcp-filesystem`, `mcp-postgres`) are in **restart loops** (RestartCount ~166/185) and repeatedly consume **~10–35% CPU** each when flapping.
- **Prometheus** is generating persistent error churn:
  - alert delivery errors to a missing Alertmanager
  - periodic TSDB directory size checks failing with `cannot allocate memory`
  - Prometheus API requests from the host to `/api/v1/query` returning “empty reply” (host port mapping instability); service-to-service queries inside the Docker network succeed

Traffic indicators:
- Host network throughput is extremely low (single-digit KB/s), inconsistent with traffic-induced load.

Overall severity: **High** for stability/operability under the current resource limits (core app itself remains light).

## Scope & Method

Collected:
- Container-level real-time metrics: CPU, memory, network IO, block IO (`docker stats`, repeated samples).
- Host-level real-time metrics: CPU %, available memory, disk bytes/sec, network bytes/sec (`Get-Counter`).
- Active process statistics (`docker top`).
- Error log analysis for Prometheus and flapping MCP containers (`docker logs`).

## Observations (Evidence)

### Host-Level Metrics (Windows)

Repeated 2s samples showed:
- **CPU:** ~35% to ~64%
- **Available memory:** ~530 MB to ~764 MB
- **Disk throughput:** ~24 MB/s to ~335 MB/s (peaks consistent with heavy container I/O)
- **Network throughput:** ~0–19 KB/s (no spike signal)

Interpretation:
- The host is **memory constrained** and regularly doing heavy disk I/O.
- Network indicates **no load from traffic**.

### Container-Level Metrics (Top Contributors)

Snapshot highlights:
- `cadvisor`: ~**1.38 GiB RAM**, frequently **~15–40% CPU**
- `prometheus`: ~**229 MB RAM**, **~0–3% CPU**, but heavy **Block I/O totals** (TSDB activity)
- `loki`: ~**90 MB RAM**, occasional **CPU bursts**
- `mcp-filesystem`, `mcp-postgres`: frequent **CPU bursts** (often **~10–35%**) with **high restart counts**

Restart counts:
- `mcp-filesystem` RestartCount ~**166**
- `mcp-postgres` RestartCount ~**185**

### Active Process Evidence

- `cadvisor` process: `/usr/bin/cadvisor -logtostderr` with long accumulated CPU time.
- `mcp-filesystem`: `npm exec @modelcontextprotocol/server-filesystem ...` (stdio server)
- `mcp-postgres`: `npm exec @modelcontextprotocol/server-postgres ...` (stdio server)

### Log Evidence (Prometheus)

Prometheus repeatedly logs:
- Alert notifier failures:
  - `dial tcp: lookup alertmanager ... no such host`
- TSDB size calculation failures:
  - `Failed to calculate size of "wal" dir ... cannot allocate memory`
  - `Failed to calculate size of "chunks_head" dir ... cannot allocate memory`

Prometheus HTTP API:
- From the host, requests to `/api/v1/query` returned empty reply (curl exit code 52).
- From inside the Docker network (e.g., `hypercode-core` → `prometheus:9090`), `/api/v1/query?query=up` returned `200`.
- `/-/ready` returned `200`.

### Log Evidence (MCP)

`mcp-filesystem` logs are spammed with:
- `Secure MCP Filesystem Server running on stdio`

`mcp-postgres` logs show npm execution churn (including npm notices), consistent with repeated container startups.

## Root Cause Analysis

### RC1 — Resource Exhaustion (Memory) in Docker Desktop

Impact:
- Causes Prometheus TSDB operations to fail allocations.
- Likely contributes to intermittent failures (including Prometheus API “empty reply”).

Evidence:
- Host available memory down to ~530 MB during sampling.
- cAdvisor consumes ~1.38 GiB alone.

Primary bottleneck location:
- **Observability stack memory footprint**, especially `cadvisor`.

### RC2 — Tooling Restart Loops (MCP stdio containers)

Impact:
- Repeated restarts generate CPU churn, log churn, and process spawn overhead.
- Competes with Core and telemetry services for limited CPU/memory.

Evidence:
- RestartCount 166/185 and repeated “running on stdio” logs.
- Repeated docker stats CPU bursts 10–35% for MCP containers.

Primary bottleneck location:
- `mcp-filesystem`, `mcp-postgres` containers running as daemons despite being stdio-oriented tools.

### RC3 — Prometheus Alerting Misconfiguration + Error Churn

Impact:
- Continuous DNS and HTTP failures increase CPU/network work and fill logs.
- Creates operational noise and masks real incidents.

Evidence:
- Prometheus logs show persistent “Error sending alerts … alertmanager … no such host”.

Primary bottleneck location:
- Prometheus notifier send loop.

### RC4 — Heavy Disk I/O (Telemetry + Containers)

Impact:
- Increases latency variability and background load.

Evidence:
- Host disk bytes/sec peaks up to ~335 MB/s.
- High cumulative container Block I/O totals for observability services.

Primary bottleneck location:
- Prometheus TSDB and general container log/data directories under Docker Desktop storage.

## Determination: Traffic Spike vs Internal Load

Not a traffic spike:
- Network throughput is negligible (KB/s).
- Core and Celery CPU are low except brief task bursts.

This is internal load from:
- observability overhead + misconfiguration
- restart loops
- constrained memory

## Recommendations (Actionable, Prioritized)

### Priority 0 — Immediate Stabilization (Today)

1. **Disable or stop MCP stdio tool containers unless actively used**
   - If MCP tooling is needed, run via the MCP gateway session manager rather than as always-on services.
   - Success criteria: RestartCount stops increasing; MCP containers consume near-zero CPU at idle.

2. **Reduce observability footprint**
   - Disable `cadvisor` if not required, or move it behind a profile.
   - If keeping it, add resource limits and/or lower collection scope.
   - Success criteria: Docker memory headroom improves (available host memory > 1.5 GiB at idle).

3. **Fix Prometheus alerting configuration**
   - Either add Alertmanager, or remove `alerting:` config from Prometheus until it exists.
   - Success criteria: Prometheus logs stop “Error sending alerts … alertmanager”.

### Priority 1 — Prevent Recurrence (This Week)

4. **Add retention and size controls for Prometheus (TSDB)**
   - Configure retention time/size to match local dev needs.
   - Enable WAL compression where applicable.
   - Success criteria: no TSDB “cannot allocate memory” messages; API queries return JSON reliably.

5. **Add retention controls for Loki**
   - Reduce log retention and chunk settings for local dev.
   - Success criteria: stable disk usage; Loki CPU remains low at idle.

6. **Increase Docker Desktop memory allocation**
   - If you want the full observability stack + agents running, allocate more than ~4 GiB to Docker Desktop.
   - Success criteria: available memory remains stable and Prometheus TSDB operations do not fail.

### Priority 2 — Performance Engineering (Ongoing)

7. **Instrument and track “background load budget”**
   - Baseline CPU/memory/disk at idle and after one swarm run.
   - Add a single dashboard panel for “top containers by CPU/memory”.

8. **Introduce profiles for heavy components**
   - Default: core + DB + redis + minimal telemetry
   - Optional profiles: `observability-full`, `agents-full`, `mcp-tools`

## Validation Plan (Confirm Fixes)

After implementing Priority 0 actions:
- Container:
  - `docker stats` shows `cadvisor` memory reduced or service stopped.
  - `mcp-filesystem` and `mcp-postgres` restart counts stop increasing.
  - Core/Celery remain healthy.
- Host:
  - Available memory stays consistently > 1.5 GiB at idle.
  - CPU at idle < 20% (excluding transient spikes).
  - Disk bytes/sec returns to low baseline outside of builds.
- Logs:
  - Prometheus logs have no “cannot allocate memory”.
  - Prometheus logs have no “Error sending alerts … alertmanager”.
- API:
  - `http://127.0.0.1:9090/api/v1/query?query=up` returns JSON consistently.
