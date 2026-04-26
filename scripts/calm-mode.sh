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
    DISCORD_ID="${FOCUS_DISCORD_ID:-${DISCORD_USER_ID:-${PETS_DISCORD_ID:-}}}"
    if [ -z "$DISCORD_ID" ] && [ -f .env ]; then
      DISCORD_ID=$(
        grep -E '^(FOCUS_DISCORD_ID|DISCORD_USER_ID|PETS_DISCORD_ID)=' .env \
          | head -n 1 \
          | cut -d= -f2 \
          | tr -d '"' \
          || true
      )
    fi

    SYNC_SECRET="${COURSE_SYNC_SECRET:-}"
    if [ -z "$SYNC_SECRET" ] && [ -f .env ]; then
      SYNC_SECRET=$(
        grep -E '^COURSE_SYNC_SECRET=' .env \
          | head -n 1 \
          | cut -d= -f2 \
          | tr -d '"' \
          || true
      )
    fi

    if [ -z "$DISCORD_ID" ]; then
      echo "💰 Token award skipped (missing DISCORD_USER_ID / FOCUS_DISCORD_ID). You still crushed it! 🔥"
    elif [ -z "$SYNC_SECRET" ]; then
      echo "💰 Token award skipped (missing COURSE_SYNC_SECRET). Set it to enable local awards."
    else
      SOURCE_ID="focus_${START}_${DISCORD_ID}"
      HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST http://localhost:8000/api/v1/economy/award-from-course \
        -H "Content-Type: application/json" \
        -H "X-Sync-Secret: ${SYNC_SECRET}" \
        -d "{\"source_id\":\"${SOURCE_ID}\",\"discord_id\":\"${DISCORD_ID}\",\"tokens\":75,\"reason\":\"Focus session complete\"}" \
        2>/dev/null || echo "000")

      if [ "$HTTP_STATUS" = "200" ]; then
        echo "🏆 75 BROski$ awarded! Nice focus session bro! ♾️"
      elif [ "$HTTP_STATUS" = "409" ]; then
        echo "🏆 Award already processed (idempotent). Nice focus session bro! ♾️"
      else
        echo "💰 Token award skipped (core offline, user not linked, or secret invalid) — you still crushed it! 🔥"
      fi
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
