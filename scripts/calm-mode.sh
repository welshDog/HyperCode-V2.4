#!/usr/bin/env bash
# Feature 5 — Calm Mode
# Restores all containers, awards BROski$ if session > 10 mins
# Uses POST /api/v1/economy/award-from-course (idempotent, auth-safe)

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
  # tr -d '\r' strips Windows CRLF from PowerShell Out-File
  START=$(cat .focus_session_start | tr -d '\r\n')
  NOW=$(date +%s)
  DURATION=$(( NOW - START ))
  DURATION_MINS=$(( DURATION / 60 ))

  echo "⏱️  Focus session: ${DURATION_MINS} minutes"

  if [ "$DURATION" -gt 600 ]; then

    # ── Resolve Discord ID (first match wins) ──────────────────────────────
    DISCORD_ID="${FOCUS_DISCORD_ID:-}"
    if [ -z "$DISCORD_ID" ]; then DISCORD_ID="${DISCORD_USER_ID:-}"; fi
    if [ -z "$DISCORD_ID" ]; then DISCORD_ID="${PETS_DISCORD_ID:-}"; fi
    # Fallback: read from .env file
    if [ -z "$DISCORD_ID" ] && [ -f .env ]; then
      for KEY in FOCUS_DISCORD_ID DISCORD_USER_ID PETS_DISCORD_ID; do
        DISCORD_ID=$(grep -E "^${KEY}=" .env | head -1 | cut -d= -f2 | tr -d '"\r' || true)
        [ -n "$DISCORD_ID" ] && break
      done
    fi
    # Last resort: git email
    if [ -z "$DISCORD_ID" ]; then
      DISCORD_ID=$(git config user.email 2>/dev/null || echo "hypercode-user")
    fi

    # ── Resolve COURSE_SYNC_SECRET ─────────────────────────────────────────
    SYNC_SECRET="${COURSE_SYNC_SECRET:-}"
    if [ -z "$SYNC_SECRET" ] && [ -f .env ]; then
      SYNC_SECRET=$(grep -E '^COURSE_SYNC_SECRET=' .env | head -1 | cut -d= -f2 | tr -d '"\r' || true)
    fi

    if [ -z "$SYNC_SECRET" ]; then
      echo "⚠️  COURSE_SYNC_SECRET not set — skipping token award."
      echo "   Set it in your shell or .env then re-run: bash scripts/calm-mode.sh"
    else
      # ── Unique source_id so this session can only award once ──────────────
      SOURCE_ID="focus_session_${START}"

      PAYLOAD=$(printf \
        '{"source_id":"%s","discord_id":"%s","tokens":75,"reason":"Focus session complete 🎯"}' \
        "$SOURCE_ID" "$DISCORD_ID")

      HTTP_STATUS=$(curl -s -o /tmp/calm_award_response.json -w "%{http_code}" \
        -X POST http://localhost:8000/api/v1/economy/award-from-course \
        -H "Content-Type: application/json" \
        -H "X-Sync-Secret: ${SYNC_SECRET}" \
        -d "$PAYLOAD" \
        2>/dev/null || echo "000")

      if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "201" ]; then
        echo "🏆 75 BROski$ awarded! Nice focus session bro! ♾️"
      elif [ "$HTTP_STATUS" = "409" ]; then
        echo "✅ Tokens already awarded for this session (idempotent — all good)."
      else
        echo "💰 Token award skipped (HTTP ${HTTP_STATUS}) — you still crushed it! 🔥"
        echo "   Response: $(cat /tmp/calm_award_response.json 2>/dev/null || echo 'none')"
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
