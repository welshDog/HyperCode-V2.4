#!/usr/bin/env bash
# scripts/calm-mode.sh — HyperCode V2.4 Calm Mode
# Brings stopped containers back up, awards BROski$ if session > 10 mins.
# Usage: make calm

set -euo pipefail

COMPOSE_FILES="-f docker-compose.yml -f docker-compose.secrets.yml"

RESTORE_SERVICES=(
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
echo "🌊 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   CALM MODE — Restoring your stack"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Spin containers back up
docker compose ${COMPOSE_FILES} up -d --no-recreate ${RESTORE_SERVICES[*]} 2>/dev/null \
  || docker compose ${COMPOSE_FILES} up -d ${RESTORE_SERVICES[*]} 2>/dev/null \
  || echo "⚠️  Some services may not be defined in compose — skipping those."

echo ""
echo "✅ Full stack restored."
echo ""

# Calculate session duration
DURATION=0
if [ -f .focus_session_start ]; then
  START=$(cat .focus_session_start)
  NOW=$(date +%s)
  DURATION=$(( NOW - START ))
  MINUTES=$(( DURATION / 60 ))
  echo "⏱️  Session duration: ${MINUTES} minutes"
  rm -f .focus_session_start
fi

# Award tokens if session was > 10 minutes (600 seconds)
if [ "${DURATION}" -gt 600 ]; then
  # Resolve Discord ID: try .env first, fallback to git user.email
  DISCORD_ID=""
  if [ -f .env ]; then
    DISCORD_ID=$(grep -E '^DISCORD_DEV_USER_ID=' .env 2>/dev/null | cut -d= -f2 || true)
  fi
  if [ -z "${DISCORD_ID}" ]; then
    DISCORD_ID=$(git config user.email 2>/dev/null || echo "dev-user")
  fi

  echo "🏆 Awarding 75 BROski\$ for your focus session..."
  RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST http://localhost:8000/api/v1/broski/award \
    -H "Content-Type: application/json" \
    -d "{\"discord_id\": \"${DISCORD_ID}\", \"amount\": 75, \"reason\": \"Focus session complete 🎯\"}" \
    2>/dev/null || echo "000")

  if [ "${RESPONSE}" = "200" ] || [ "${RESPONSE}" = "201" ]; then
    echo "✅ 75 BROski\$ awarded to ${DISCORD_ID}!"
  else
    echo "⚠️  Token award skipped (core not responding or endpoint not wired yet)."
    echo "   Manual award: POST /api/v1/broski/award {discord_id, amount: 75}"
  fi
else
  echo "ℹ️  Session < 10 mins — no tokens awarded this time. You've got this next time! 💪"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  You built 29 containers. Today is just one more step. 🏆"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
