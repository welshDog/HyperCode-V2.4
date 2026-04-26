#!/usr/bin/env bash
# scripts/focus-mode.sh — HyperCode V2.4 Focus Mode
# Stops non-essential containers, keeps the core running, starts a 25-min timer.
# Usage: make focus

set -euo pipefail

CORE_ONLY_CONTAINERS=(
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
echo "🎯 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   FOCUS MODE ACTIVATED"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

Stopped=0
for container in "${CORE_ONLY_CONTAINERS[@]}"; do
  if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
    docker stop "${container}" > /dev/null 2>&1 && echo "  ⏸  Stopped: ${container}" && ((Stopped++)) || true
  fi
done

echo ""
echo "✅ ${Stopped} non-essential containers stopped."
echo "🟢 Core stack running: hypercode-core, redis, postgres, broski-bot, healer-agent"
echo ""

# Write timestamp for calm-mode to calculate duration
date +%s > .focus_session_start
echo "⏱️  25 minute timer started. GO. 🔥"
echo ""

# Background timer — notifies when 25 mins are up
(
  sleep 1500
  echo ""
  echo "⏰  25 mins up! Run 'make calm' to restore everything and claim your BROski\$! 🏆"
  # Desktop notify if available (Linux/WSL with libnotify)
  notify-send "HyperCode" "Focus session complete! Run make calm 🏆" 2>/dev/null || true
) &

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  One task. One win. That's the whole plan. 🎯"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
