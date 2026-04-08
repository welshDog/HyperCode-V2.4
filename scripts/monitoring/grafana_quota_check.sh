#!/usr/bin/env bash
# =============================================================
# HyperCode — Grafana OSS Stack Quota & Health Check
# Version: 1.0  |  Target: Grafana 12.x + Prometheus + Loki
# Usage:   bash grafana_quota_check.sh
# Cron:    0 9 1 * * /path/to/grafana_quota_check.sh >> /var/log/grafana_quota.log 2>&1
# =============================================================

set -euo pipefail

# ── CONFIG ────────────────────────────────────────────────────
GRAFANA_URL="${GRAFANA_URL:-http://localhost:3001}"
PROM_URL="${PROM_URL:-http://localhost:9090}"
LOKI_URL="${LOKI_URL:-http://localhost:3100}"
GRAFANA_USER="${GRAFANA_USER:-lyndzwills}"
GRAFANA_PASS="${GRAFANA_PASS:-password}"   # override with env var
# Replace with your actual username and password or use an API Token
GRAFANA_AUTH="${GRAFANA_USER}:${GRAFANA_PASS}"

# Thresholds — edit to suit your host disk
PROM_WARN_GB=3.0
PROM_CRIT_GB=4.5
LOKI_WARN_GB=8.0
LOKI_CRIT_GB=12.0
DASH_WARN=150
ALERT_WARN=80
ANNOTATION_WARN=50000

# Discord webhook (optional — leave blank to skip)
DISCORD_WEBHOOK="${DISCORD_WEBHOOK:-}"

# ── COLOURS ───────────────────────────────────────────────────
RED='\033[0;31m'; YEL='\033[1;33m'; GRN='\033[0;32m'
CYA='\033[0;36m'; BLD='\033[1m'; RST='\033[0m'

DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "======================================"
ISSUES=()

# ── HELPERS ───────────────────────────────────────────────────
gapi() { curl -sf -u "${GRAFANA_USER}:${GRAFANA_PASS}" "${GRAFANA_URL}${1}"; }
papi() { curl -sf "${PROM_URL}/api/v1/query?query=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$1")"; }
lapi() { curl -sf "${LOKI_URL}${1}" 2>/dev/null || echo '{}'; }

scalar() {
  # Extract first scalar value from Prometheus JSON response
  python3 -c "
import sys, json
d = json.load(sys.stdin)
r = d.get('data',{}).get('result',[])
print(r[0]['value'][1] if r else '0')
" <<< "$1"
}

gb() { echo "scale=2; ${1:-0} / 1073741824" | bc; }
mb() { echo "scale=1; ${1:-0} / 1048576" | bc; }

warn()  { echo -e "${YEL}  ⚠ WARN  ${RST} $*"; ISSUES+=("WARN: $*"); }
crit()  { echo -e "${RED}  ✖ CRIT  ${RST} $*"; ISSUES+=("CRIT: $*"); }
ok()    { echo -e "${GRN}  ✔ OK    ${RST} $*"; }
info()  { echo -e "${CYA}  ℹ INFO  ${RST} $*"; }
header(){ echo -e "\n${BLD}${CYA}━━━ $* ━━━${RST}"; }

compare_gb() {
  local value=$1 warn=$2 crit=$3 label=$4
  if (( $(echo "$value >= $crit" | bc -l) )); then
    crit "${label}: ${value} GB  (critical threshold: ${crit} GB)"
  elif (( $(echo "$value >= $warn" | bc -l) )); then
    warn "${label}: ${value} GB  (warning threshold: ${warn} GB)"
  else
    ok   "${label}: ${value} GB"
  fi
}

compare_int() {
  local value=$1 warn=$2 label=$3
  if (( value >= warn )); then
    warn "${label}: ${value}  (warning threshold: ${warn})"
  else
    ok   "${label}: ${value}"
  fi
}

# ── HEADER ────────────────────────────────────────────────────
echo -e "\n${BLD}╔══════════════════════════════════════════════════════╗"
echo -e "║   HyperCode — Grafana OSS Quota & Health Check        ║"
echo -e "║   ${DATE}                    ║"
echo -e "╚══════════════════════════════════════════════════════╝${RST}"

# ── 1. GRAFANA HEALTH ─────────────────────────────────────────
header "1. Grafana OSS Health"
HEALTH=$(curl -sf "${GRAFANA_URL}/api/health" 2>/dev/null || echo '{"database":"error"}')
DB_STATUS=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('database','unknown'))")
GF_VERSION=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('version','unknown'))")

if [[ "$DB_STATUS" == "ok" ]]; then
  ok "Grafana database: OK (v${GF_VERSION})"
else
  crit "Grafana database status: ${DB_STATUS}"
fi

# ── 2. GRAFANA INSTANCE STATS ─────────────────────────────────
header "2. Grafana Instance Stats"

DASH_COUNT=$(gapi "/api/search?limit=5000&type=dash-db" 2>/dev/null | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)
compare_int "$DASH_COUNT" "$DASH_WARN" "Dashboards"

DS_COUNT=$(gapi "/api/datasources" 2>/dev/null | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)
ok "Data sources: ${DS_COUNT}"

USER_COUNT=$(gapi "/api/org/users" 2>/dev/null | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)
ok "Users in org: ${USER_COUNT}"

ALERT_COUNT=$(gapi "/api/v1/provisioning/alert-rules" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d) if isinstance(d,list) else 0)" 2>/dev/null || echo 0)
compare_int "$ALERT_COUNT" "$ALERT_WARN" "Alert rules"

PLUGIN_COUNT=$(gapi "/api/plugins?embedded=0" 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(len([p for p in d if p.get('enabled')]))" 2>/dev/null || echo 0)
ok "Enabled plugins: ${PLUGIN_COUNT}"

# ── 3. ANNOTATION BLOAT ───────────────────────────────────────
header "3. Grafana Database — Annotation Bloat"
ANNO_COUNT=$(gapi "/api/annotations?limit=1&from=0&to=$(date +%s)000" 2>/dev/null \
  | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "unknown")
info "Annotations sample returned: ${ANNO_COUNT} (use DB query for exact count)"
echo -e "  ${YEL}Tip:${RST} Run inside Grafana container:"
echo -e "       sqlite3 /var/lib/grafana/grafana.db 'SELECT COUNT(*) FROM annotation;'"

DB_SIZE_BYTES=$(docker exec grafana du -sb /var/lib/grafana/grafana.db 2>/dev/null | awk '{print $1}' || echo 0)
DB_SIZE_MB=$(mb "$DB_SIZE_BYTES")
if (( $(echo "$DB_SIZE_MB > 200" | bc -l) )); then
  warn "Grafana SQLite DB size: ${DB_SIZE_MB} MB  (recommend pruning annotations)"
else
  ok   "Grafana SQLite DB size: ${DB_SIZE_MB} MB"
fi

# ── 4. PROMETHEUS ─────────────────────────────────────────────
header "4. Prometheus Storage & Metrics"

PROM_HEALTH=$(curl -sf "${PROM_URL}/-/healthy" 2>/dev/null || echo "ERROR")
if [[ "$PROM_HEALTH" == *"Healthy"* ]]; then
  ok "Prometheus process: Healthy"
else
  crit "Prometheus process: UNREACHABLE at ${PROM_URL}"
fi

PROM_BYTES_RAW=$(papi "prometheus_tsdb_storage_blocks_bytes" 2>/dev/null)
PROM_BYTES=$(scalar "$PROM_BYTES_RAW")
PROM_GB=$(gb "$PROM_BYTES")
compare_gb "$PROM_GB" "$PROM_WARN_GB" "$PROM_CRIT_GB" "Prometheus TSDB (blocks)"

PROM_WAL_RAW=$(papi "prometheus_tsdb_wal_storage_size_bytes" 2>/dev/null)
PROM_WAL=$(scalar "$PROM_WAL_RAW")
PROM_WAL_MB=$(mb "$PROM_WAL")
ok "Prometheus WAL size: ${PROM_WAL_MB} MB"

PROM_SERIES_RAW=$(papi "prometheus_tsdb_head_series" 2>/dev/null)
PROM_SERIES=$(scalar "$PROM_SERIES_RAW")
ok "Active Prometheus series: ${PROM_SERIES}"

PROM_RETENTION_RAW=$(papi "prometheus_tsdb_retention_limit_bytes" 2>/dev/null)
PROM_RETENTION=$(scalar "$PROM_RETENTION_RAW")
if [[ "$PROM_RETENTION" != "0" && "$PROM_RETENTION" != "" ]]; then
  PROM_RETENTION_GB=$(gb "$PROM_RETENTION")
  ok "Prometheus retention size limit: ${PROM_RETENTION_GB} GB"
else
  warn "Prometheus retention size limit: NOT SET  (add --storage.tsdb.retention.size=5GB)"
fi

PROM_SCRAPE_ERRORS_RAW=$(papi "sum(up == 0)" 2>/dev/null)
PROM_SCRAPE_ERRORS=$(scalar "$PROM_SCRAPE_ERRORS_RAW")
if (( $(echo "${PROM_SCRAPE_ERRORS:-0} > 0" | bc -l) 2>/dev/null )); then
  warn "Prometheus scrape targets DOWN: ${PROM_SCRAPE_ERRORS}"
else
  ok   "All Prometheus scrape targets: UP"
fi

# ── 5. LOKI ───────────────────────────────────────────────────
header "5. Loki Log Storage"

LOKI_READY=$(curl -sf "${LOKI_URL}/ready" 2>/dev/null || echo "ERROR")
if [[ "$LOKI_READY" == *"ready"* ]]; then
  ok "Loki process: Ready"
else
  crit "Loki process: UNREACHABLE at ${LOKI_URL}"
fi

LOKI_DIR_BYTES=$(docker exec loki du -sb /loki/chunks 2>/dev/null | awk '{print $1}' || echo 0)
LOKI_DIR_GB=$(gb "$LOKI_DIR_BYTES")
compare_gb "$LOKI_DIR_GB" "$LOKI_WARN_GB" "$LOKI_CRIT_GB" "Loki chunks on disk"

LOKI_INGESTION_RATE_RAW=$(papi "sum(rate(loki_ingester_bytes_received_total[5m]))" 2>/dev/null)
LOKI_INGESTION_RATE=$(scalar "$LOKI_INGESTION_RATE_RAW")
LOKI_RATE_KB=$(echo "scale=1; ${LOKI_INGESTION_RATE:-0} / 1024" | bc 2>/dev/null || echo "0")
ok "Loki current ingestion rate: ${LOKI_RATE_KB} KB/s"

# ── 6. TEMPO ──────────────────────────────────────────────────
header "6. Tempo Trace Storage"

TEMPO_HEALTH=$(curl -sf "http://localhost:3200/ready" 2>/dev/null || echo "ERROR")
if [[ "$TEMPO_HEALTH" == *"ready"* ]]; then
  ok "Tempo process: Ready"
else
  warn "Tempo process: UNREACHABLE at http://localhost:3200"
fi

TEMPO_DIR_BYTES=$(docker exec tempo du -sb /var/tempo 2>/dev/null | awk '{print $1}' || echo 0)
TEMPO_DIR_GB=$(gb "$TEMPO_DIR_BYTES")
ok "Tempo data on disk: ${TEMPO_DIR_GB} GB"

# ── 7. DOCKER CONTAINER HEALTH ────────────────────────────────
header "7. Docker Container Status"
for CONTAINER in grafana prometheus loki tempo; do
  STATUS=$(docker inspect --format='{{.State.Status}}' "$CONTAINER" 2>/dev/null || echo "not found")
  RESTARTS=$(docker inspect --format='{{.RestartCount}}' "$CONTAINER" 2>/dev/null || echo "0")
  if [[ "$STATUS" == "running" ]]; then
    if (( RESTARTS > 3 )); then
      warn "Container ${CONTAINER}: running  (${RESTARTS} restarts — investigate)"
    else
      ok "Container ${CONTAINER}: running  (restarts: ${RESTARTS})"
    fi
  else
    crit "Container ${CONTAINER}: ${STATUS}"
  fi
done

# Docker disk usage summary
DOCKER_DISK=$(docker system df --format "table {{.Type}}\t{{.Size}}\t{{.Reclaimable}}" 2>/dev/null || echo "unavailable")
echo -e "\n  Docker disk overview:"
echo "$DOCKER_DISK" | sed 's/^/    /'

# ── 8. HOST DISK ──────────────────────────────────────────────
header "8. Host Disk Space"
df -h / /var/lib/docker 2>/dev/null | awk 'NR==1 || /\/$/ || /docker/' | while read -r line; do
  USE_PCT=$(echo "$line" | awk '{print $5}' | tr -d '%' 2>/dev/null || echo 0)
  if [[ "$USE_PCT" =~ ^[0-9]+$ ]]; then
    if (( USE_PCT >= 90 )); then
      echo -e "${RED}  ✖ CRIT  ${RST} $line"
    elif (( USE_PCT >= 80 )); then
      echo -e "${YEL}  ⚠ WARN  ${RST} $line"
    else
      ok "Disk usage: $line"
    fi
  fi
done

echo -e "\nCheck complete. Log saved to /var/log/grafana_quota.log (if configured)."
