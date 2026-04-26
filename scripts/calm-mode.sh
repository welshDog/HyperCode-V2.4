#!/usr/bin/env bash
# Feature 5 — Calm Mode
# Restores all containers, awards BROski$ if session > 10 mins

set -euo pipefail

CALM_CONTAINERS=(
  grafana
  prometheus
  loki
  tempo
  promtail
  cadvisor
  node-exporter
  minio
  chroma
  hypercode-dashboard
  hyper-mission-api
  hyper-mission-ui
  alertmanager
  celery-exporter
)

echo ""
echo "🌊 CALM MODE — Restoring everything..."
echo ""

# Spin containers back up
docker compose \
  -f docker-compose.yml \
  -f docker-compose.secrets.yml \
  up -d "${CALM_CONTAINERS[@]}" 2>/dev/null || true

echo ""
echo "✅ All containers restored."

# Calculate session duration + award tokens if > 10 mins
if [ -f .focus_session_start ]; then
  START=$(cat .focus_session_start)
  NOW=$(date +%s)
  DURATION=$(( NOW - START ))
  DURATION_MINS=$(( DURATION / 60 ))

  echo "⏱️  Focus session: ${DURATION_MINS} minutes"

  if [ "$DURATION" -gt 600 ]; then
    # Get discord_id from .env or git email fallback
    DISCORD_ID=""
    if [ -f .env ]; then
      DISCORD_ID=$(grep -E '^DISCORD_USER_ID=' .env | cut -d= -f2 | tr -d '"' || true)
    fi
    if [ -z "$DISCORD_ID" ]; then
      DISCORD_ID=$(git config user.email 2>/dev/null || echo "hypercode-user")
    fi

    # Award BROski$
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
      -X POST http://localhost:8000/api/v1/broski/award \
      -H "Content-Type: application/json" \
      -d "{\"discord_id\": \"${DISCORD_ID}\", \"amount\": 75, \"reason\": \"Focus session complete \\ud83c\\udfaf\"}" \
      2>/dev/null || echo "000")

    if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "201" ]; then
      echo "🏆 75 BROski$ awarded! Nice focus session bro! ♾️"
    else
      echo "💰 Token award skipped (core offline or endpoint missing) — you still crushed it! 🔥"
    fi
  else
    echo "⚡ Session under 10 mins — no tokens this time. Longer next session! 💪"
  fi

  rm -f .focus_session_start
else
  echo "ℹ️  No active focus session found."
fi

echo ""
echo "🌊 CALM MODE — Stack fully restored. Welcome back, BROski♾️"
echo ""
