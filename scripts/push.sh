#!/usr/bin/env bash
# Dashboard promotion: local dev → Grafana Cloud
# Usage: GRAFANA_URL=https://hypercode.grafana.net GRAFANA_TOKEN=glsa_xxx ./scripts/push.sh dashboards/hypercode/hyperhealth-overview.json
#
# RULES (do not break):
#   1. One UID per dashboard — same across all envs
#   2. Never edit dashboards directly in Cloud UI — export → commit → push
#   3. Folders mirror repo structure

set -euo pipefail

if [[ -z "${GRAFANA_URL:-}" || -z "${GRAFANA_TOKEN:-}" ]]; then
  echo "❌ Set GRAFANA_URL and GRAFANA_TOKEN first."
  echo "   export GRAFANA_URL=https://hypercode.grafana.net"
  echo "   export GRAFANA_TOKEN=glsa_your_token_here"
  exit 1
fi

FILE=$1

if [[ ! -f "$FILE" ]]; then
  echo "❌ File not found: $FILE"
  exit 1
fi

# Derive folder name from parent directory
FOLDER_TITLE=$(basename "$(dirname "$FILE")")
FOLDER_UID=$(echo -n "$FOLDER_TITLE" | md5sum | cut -c1-8)

echo "📁 Folder: $FOLDER_TITLE (uid: $FOLDER_UID)"
echo "📊 Dashboard: $FILE"

# Get or create folder (ignore 412 = already exists)
curl -sf -o /dev/null -X POST "$GRAFANA_URL/api/folders" \
  -H "Authorization: Bearer $GRAFANA_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"uid\":\"$FOLDER_UID\",\"title\":\"$FOLDER_TITLE\"}" || true

# Remap datasource UID for Cloud Prometheus
# Replace ${DS_PROMETHEUS} placeholder with actual Cloud datasource UID
CLOUD_PROM_UID="${CLOUD_PROM_UID:-grafanacloud-prom}"

PAYLOAD=$(jq \
  --arg folder "$FOLDER_UID" \
  --arg ds_uid "$CLOUD_PROM_UID" \
  '(walk(if type == "object" and .uid == "${DS_PROMETHEUS}" then .uid = $ds_uid else . end)) |
   {dashboard: ., folderUid: $folder, overwrite: true, message: "Promoted via CI"}' \
  "$FILE")

RESPONSE=$(curl -sf -X POST "$GRAFANA_URL/api/dashboards/db" \
  -H "Authorization: Bearer $GRAFANA_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD")

STATUS=$(echo "$RESPONSE" | jq -r '.status // "unknown"')
URL=$(echo "$RESPONSE" | jq -r '.url // ""')

if [[ "$STATUS" == "success" ]]; then
  echo "✅ Promoted: $GRAFANA_URL$URL"
else
  echo "❌ Failed: $RESPONSE"
  exit 1
fi
