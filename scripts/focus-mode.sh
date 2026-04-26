#!/usr/bin/env bash
# Feature 5 — Focus Mode
# Stops non-essential containers, starts 25-min timer

set -euo pipefail

FOCUS_CONTAINERS=(
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
echo "🎯 FOCUS MODE ACTIVATING..."
echo ""

STOPPED=0
for svc in "${FOCUS_CONTAINERS[@]}"; do
  if docker ps --format '{{.Names}}' | grep -q "^${svc}$"; then
    docker stop "$svc" > /dev/null 2>&1 && echo "  ⏸  Stopped: $svc" && ((STOPPED++)) || true
  fi
done

echo ""
echo "✅ FOCUS MODE — $STOPPED containers stopped. Core stack running."
echo "   Kept alive: hypercode-core | redis | postgres | broski-bot | healer-agent"
echo ""
echo "⏱️  25 minute timer started. GO. 🚀"
echo ""

# Write session start timestamp
date +%s > .focus_session_start

# Background 25-min countdown — cross-platform notify
(
  sleep 1500
  echo ""
  echo "⏰ 25 mins up! Run 'make calm' to restore everything and grab your BROski$ 🏆"
  echo ""
  notify-send "HyperCode" "Focus session complete! Run make calm 🏆" 2>/dev/null || true
) &

echo "💡 Tip: Run 'make calm' when done to restore + earn 75 BROski$"
echo ""
