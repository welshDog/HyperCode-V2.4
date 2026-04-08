# Grafana OSS v12.3.3 — Complete Evaluation Report
*Instance: `localhost:3001` | Instance ID: `1458b4a88824` | Admin: `lyndzwills`*

***

## Your Instance — What's Running Right Now

From the live exploration: [localhost](http://localhost:3001/admin/upgrading)

| Stat | Value |
|---|---|
| Version | **12.3.3** (latest stable)  [localhost](http://localhost:3001/api/health) |
| License | **OSS** (no Enterprise license — free forever) |
| Dashboards | 1 starred |
| Data Sources | **3** — Loki (`http://loki:3100`), Prometheus (`http://prometheus:9090` — default), Tempo (`http://tempo:3200`) |
| Organisations | 1 |
| Users total | 1 |
| Active sessions | 2 |
| Alert rules | 3 rules (1 error, 3 normal) — "HyperCode Infrastructure" + "agent_health" |
| Database | SQLite3 (`/var/lib/grafana/grafana.db`) |
| Data path | `/var/lib/grafana` |
| Plugin path | `/var/lib/grafana/plugins` |
| Log retention | 7 days (max_days=7) |

***

## 1. Core Functionality and Key Features

**Grafana OSS** is a fully free, open-source analytics and visualisation platform. Running self-hosted in Docker, it has **no paywalls, no quotas, and no billing** — all limits are set by your own hardware. [localhost](http://localhost:3001/admin/settings)

| Feature | Available in OSS |
|---|---|
| Unlimited dashboards | Yes |
| Unlimited users | Yes (quota off by default) |
| Unified Alerting (Grafana-managed rules) | Yes  [localhost](http://localhost:3001/alerting/list) |
| Prometheus, Loki, Tempo data sources | Yes — all 3 wired  [localhost](http://localhost:3001/connections/datasources) |
| Provisioning via YAML/files | Yes (`/etc/grafana/provisioning`) |
| Public dashboards | Yes (enabled in config) |
| Plugin marketplace install | Yes (admin-enabled) |
| RBAC (Role-Based Access Control) | Yes (enabled) |
| Explore + Drilldown | Yes |
| API access | Yes (full HTTP API) |
| Correlations (cross-datasource links) | Yes |
| Snapshots | Yes |

**What is NOT in OSS (requires Enterprise):**
- Data source permissions (row-level)
- Reporting (scheduled PDF/CSV exports)
- SAML / Enhanced LDAP / Team Sync
- White-labelling
- Enterprise plugins (Oracle, Splunk, ServiceNow, etc.) [localhost](http://localhost:3001/admin/upgrading)

***

## 2. Strengths, Limitations, and Suitability

### Strengths
- **Truly unlimited** — no metrics cap, no log cap, no user cap at the Grafana layer. Your only limits are Prometheus TSDB storage and Loki chunk storage on your Docker host.
- **Full observability trio already wired** — Prometheus + Loki + Tempo already connected. [localhost](http://localhost:3001/connections/datasources)
- **Alert rules already provisioned** — HyperCode Infrastructure rules are live. [localhost](http://localhost:3001/alerting/list)
- **v12.3.3** is one of the most feature-complete OSS versions ever — includes Drilldown, Correlations, unified alerting, RBAC.
- **Zero dependency on Grafana Cloud** — works completely offline.

### Limitations
- **Storage is on your host** — if Docker volume fills up, Prometheus stops ingesting.
- **No built-in auth SSO** unless you configure OAuth manually (GitHub/GitLab/Google/Okta config blocks are present but all `enabled: false` in your `grafana.ini`). [localhost](http://localhost:3001/admin/settings)
- **SQLite3 database** (not MySQL/Postgres) — fine for solo/small team, but not HA-ready.
- **No auto-scaling** — you manage memory/CPU resources for all containers.
- **max_annotations_to_keep = 0** (unlimited) in your current config — can cause DB bloat over time.

### Suitability for HyperCode
- **Ideal** for monitoring Docker containers, FastAPI agents, and AI pipelines with zero cost.
- The existing HyperCode Infrastructure + agent_health alert rules show the stack is already partially instrumented.

***

## 3. Account Setup — Self-Hosted (No Payment Required)

Since you're running Grafana OSS in Docker, there is no account to create and no payment info is ever requested. Here's the canonical setup path for a fresh install:

```bash
# Step 1 — Pull and run (Docker)
docker run -d \
  --name=grafana \
  -p 3001:3000 \
  -v grafana-storage:/var/lib/grafana \
  -e GF_SECURITY_ADMIN_USER=your_username \
  -e GF_SECURITY_ADMIN_PASSWORD=your_password \
  grafana/grafana-oss:12.3.3

# Step 2 — First login
# Open http://localhost:3001
# Username: your_username / Password: your_password
# No email, no payment, no trial — fully operational immediately

# Step 3 — Verify OSS (no enterprise license page = free)
curl http://localhost:3001/api/health
# Returns: {"database":"ok","version":"12.3.3",...}
```

**Eligibility:** All humans. No restrictions. Grafana OSS is Apache 2.0 licensed.

***

## 4. Configuration Checklist to Maximise Free Tier

### grafana.ini / Environment Variables Optimisation

```ini
[quota]
enabled = true               # TURN ON to protect yourself from runaway scripts
org_dashboard = 500          # Max dashboards per org (default 100 — raise to 500)
org_data_source = 50         # Max data sources per org (default 10)
org_api_key = 50             # Max API keys per org (default 10)
org_user = 100               # Max users per org (default 10)
global_dashboard = -1        # No global cap

[dashboards]
versions_to_keep = 5         # Default 20 — reduce to save SQLite space
min_refresh_interval = 10s   # Prevent <10s panel refresh hammering

[annotations]
# Prevent annotations table growing infinitely
cleanupjob_batchsize = 100
[annotations.api]
max_annotations_to_keep = 1000
max_age = 30d
[annotations.dashboard]
max_annotations_to_keep = 500
max_age = 14d
# Your current config has max_annotations_to_keep = 0 (UNLIMITED — fix this!)

[database]
wal = true                   # Enable WAL mode for SQLite — better write performance

[log.file]
max_days = 14                # Default 7 — extend slightly
max_size_shift = 28          # ~256MB max log file

[alerting]
evaluation_timeout_seconds = 30
min_interval_seconds = 10    # Minimum 10s eval interval (already set) [web:13]

[server]
enable_gzip = true           # Compress HTTP responses — saves bandwidth
```

### Prometheus Retention (critical — controls your main storage cost)

```yaml
# In your docker-compose.yml, prometheus service:
command:
  - '--config.file=/etc/prometheus/prometheus.yml'
  - '--storage.tsdb.path=/prometheus'
  - '--storage.tsdb.retention.time=15d'   # Keep 15 days (default is 15d already)
  - '--storage.tsdb.retention.size=5GB'   # Hard cap at 5GB disk usage
  - '--web.enable-lifecycle'               # Allows hot reload
```

### Loki Retention

```yaml
# In loki-config.yaml:
limits_config:
  retention_period: 336h    # 14 days
  ingestion_rate_mb: 4      # 4MB/s max ingest rate
  max_global_streams_per_user: 5000

compactor:
  retention_enabled: true
  working_directory: /loki/compactor
```

***

## 5. Usage Best Practices

### Rate-Limiting Dashboard Queries
- Set **minimum refresh interval** to `10s` in `grafana.ini` (already done — `min_refresh_interval = 5s`, raise to `10s`).
- Use **`$__interval`** template variable in PromQL instead of hardcoded `[1m]` — auto-adapts to time range.
- Limit panels to **one query per panel** where possible.

### Caching
```ini
[caching]
enabled = true   # Already true in your config [web:13] — good
```
- Use Prometheus **recording rules** (already configured — `recording_rules.enabled = true`) to pre-compute expensive queries.

### Job Batching
- Group alert rule evaluations in folders so they share evaluation cycles.
- Your existing Grafana-managed rules use `1m` evaluation interval  — optimal. [localhost](http://localhost:3001/alerting/list)

### Data Retention Policies
| Component | Recommended Retention | Your Config |
|---|---|---|
| Prometheus | 15 days | Check `storage.tsdb.retention.time` |
| Loki | 14 days | Set `retention_period: 336h` in loki-config |
| Grafana annotations | 30 days, max 1000 | Currently UNLIMITED — fix needed |
| Grafana dashboard versions | 5 | Currently 20 — reduce |
| Grafana log files | 14 days | Currently 7 days |
| Tempo traces | 48h | Default in OSS Tempo |

### Monitoring Alerts to Stay Within Limits
Create a PromQL alert rule:
```promql
# Prometheus TSDB disk usage alert
(prometheus_tsdb_storage_blocks_bytes / 1024 / 1024 / 1024) > 4
# Fires when Prometheus uses >4GB
```

***

## 6. Automated Safeguards

### Grafana Alert Rule for Prometheus Storage

```yaml
# Paste into Alerting → Alert rules → New alert rule
Name: Prometheus Storage Critical
Query A: prometheus_tsdb_storage_blocks_bytes / 1024 / 1024 / 1024
Condition: IS ABOVE 4
Evaluation: every 1m, for 5m
Contact point: (set up a Discord/email webhook)
```

### Webhook Contact Point (Discord)
```
Alerting → Contact points → Add contact point
Type: Discord or Webhook
URL: https://discord.com/api/webhooks/YOUR_WEBHOOK
```

### CLI Safeguard — Prometheus Storage Watch Script

```bash
#!/bin/bash
# save as: watch_prometheus.sh
# Run via cron: */15 * * * * /path/to/watch_prometheus.sh

LIMIT_GB=4.5
PROM_URL="http://localhost:9090"

USED=$(curl -s "${PROM_URL}/api/v1/query?query=prometheus_tsdb_storage_blocks_bytes" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(float(d['data']['result'][0]['value'] [localhost](http://localhost:3001/admin/upgrading))/1e9)")

echo "Prometheus storage: ${USED} GB"

if (( $(echo "$USED > $LIMIT_GB" | bc -l) )); then
  echo "WARNING: Prometheus at ${USED}GB — above ${LIMIT_GB}GB threshold"
  # Optionally post to Discord:
  # curl -H "Content-Type: application/json" \
  #   -d "{\"content\":\"ALERT: Prometheus storage at ${USED}GB\"}" \
  #   "$DISCORD_WEBHOOK_URL"
fi
```

### grafana.ini Quota Guardrails (enable these now)
```ini
[quota]
enabled = true
org_dashboard = 200
org_alert_rule = 100      # Already set [web:13]
alerting_rule_group_rules = 100   # Already set
```

***

## 7. What Becomes Unavailable After Limits Are Exhausted

**For Grafana OSS (self-hosted) — there are no cloud billing limits.** Nothing becomes "unavailable" due to quota unless you enable `[quota] enabled = true` yourself. The only real exhaustion scenarios are:

| Resource Exhausted | What Happens | How to Recover |
|---|---|---|
| Prometheus disk full | New metrics silently dropped, TSDB may corrupt | Reduce retention or expand Docker volume |
| Loki disk full | Log ingestion stops with 429 errors | Compact old chunks, run `loki-canary` to check |
| SQLite DB grows too large | Grafana API slows down | Enable WAL mode, prune annotations, reduce dashboard versions |
| Docker container OOM | Container crashes and restarts | Set `mem_limit` in docker-compose |

### Data Export Before Hitting Limits

```bash
# Export all Grafana dashboards as JSON
curl -s http://admin:${GRAFANA_PASSWORD}@localhost:3001/api/search?limit=1000 \
  | jq -r '.[].uid' \
  | while read uid; do
      curl -s "http://admin:${GRAFANA_PASSWORD}@localhost:3001/api/dashboards/uid/$uid" \
        > "backup_${uid}.json"
    done

# Export Prometheus data (last 7 days) using promtool
docker exec prometheus promtool tsdb dump /prometheus > prometheus_dump.txt

# Export all alert rules
curl -s http://admin:${GRAFANA_PASSWORD}@localhost:3001/api/v1/provisioning/alert-rules \
  > alert_rules_backup.json
```

***

## 8. Deliverables

### A. Quota Tracking Script (copy-paste ready)

```bash
#!/bin/bash
# ============================================
# HyperCode Grafana Stack — Monthly Quota Check
# Run: bash grafana_quota_check.sh
# ============================================

GRAFANA_URL="http://localhost:3001"
PROM_URL="http://localhost:9090"
GRAFANA_AUTH="lyndzwills:${GRAFANA_PASSWORD}"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "======================================"
echo " HyperCode Grafana Quota Check"
echo " $DATE"
echo "======================================"

# 1. Grafana instance stats
echo -e "\n--- Grafana OSS Stats ---"
STATS=$(curl -s -u "$GRAFANA_AUTH" "$GRAFANA_URL/api/org/users" | jq 'length')
echo "Active users: $STATS"
DASH_COUNT=$(curl -s -u "$GRAFANA_AUTH" "$GRAFANA_URL/api/search?limit=5000" | jq 'length')
echo "Total dashboards: $DASH_COUNT"
DS_COUNT=$(curl -s -u "$GRAFANA_AUTH" "$GRAFANA_URL/api/datasources" | jq 'length')
echo "Data sources: $DS_COUNT"
ALERT_COUNT=$(curl -s -u "$GRAFANA_AUTH" "$GRAFANA_URL/api/v1/provisioning/alert-rules" | jq 'length')
echo "Alert rules: $ALERT_COUNT"

# 2. Prometheus storage
echo -e "\n--- Prometheus Storage ---"
PROM_BYTES=$(curl -s "${PROM_URL}/api/v1/query?query=prometheus_tsdb_storage_blocks_bytes" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); \
    r=d['data']['result']; print(r[0]['value'] [localhost](http://localhost:3001/admin/upgrading) if r else 0)" 2>/dev/null)
PROM_GB=$(echo "scale=2; $PROM_BYTES / 1073741824" | bc 2>/dev/null || echo "N/A")
echo "Prometheus TSDB used: ${PROM_GB} GB"

PROM_SERIES=$(curl -s "${PROM_URL}/api/v1/query?query=prometheus_tsdb_head_series" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); \
    r=d['data']['result']; print(r[0]['value'][1] if r else 0)" 2>/dev/null)
echo "Active time series: $PROM_SERIES"

# 3. Docker Container Health
echo -e "\n--- Container Status ---"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "grafana|prometheus|loki|tempo"

echo -e "\nCheck complete. Save output to reports/ if needed."
```

### B. Monthly Compliance Checklist (Reusable)

**File:** `GRAFANA_MONTHLY_CHECKLIST.md`

| Category | Check Item | Threshold | Status (Pass/Fail) | Notes |
|---|---|---|---|---|
| **Storage** | Prometheus TSDB Size | < 5GB | [ ] | Current: ____ GB |
| **Storage** | Loki Chunk Store | < 5GB | [ ] | Current: ____ GB |
| **Performance** | Active Series Count | < 100k | [ ] | Current: ____ |
| **Grafana** | Dashboard Count | < 500 | [ ] | Current: ____ |
| **Grafana** | Annotation Count | < 1000 | [ ] | **Action needed if high** |
| **Security** | Public Dashboards | Disabled | [ ] | Check `[auth.anonymous]` |
| **Security** | Users/API Keys | Reviewed | [ ] | Remove unused keys |
| **Backups** | Dashboards Exported | Yes | [ ] | JSON export done |
| **Backups** | Alert Rules Exported | Yes | [ ] | YAML/JSON export done |
| **System** | Docker Container Health | Up > 99% | [ ] | Check `docker ps` |

*Run the quota script above to populate the values.*

***

**End of Report**
