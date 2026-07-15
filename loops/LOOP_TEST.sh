#!/bin/bash
# LOOP_TEST.sh — HyperCode-V2.4 smoke test
# Claude runs this at the end of every container loop

echo "🔍 HyperFocus Z0ne — Loop Smoke Test"
echo "======================================"

PASS=0
FAIL=0

check() {
  local name=$1
  local cmd=$2
  if eval "$cmd" > /dev/null 2>&1; then
    echo "  ✅ $name"
    ((PASS++))
  else
    echo "  ❌ $name — FAILED"
    ((FAIL++))
  fi
}

check "FastAPI core health"     "curl -sf http://localhost:8000/health"
check "Brain engine health"     "curl -sf http://localhost:8100/health"
check "Redis ping"              "docker exec redis redis-cli ping | grep -q PONG"
check "Postgres ready"          "docker exec postgres pg_isready -q"
check "Prometheus ready"        "curl -sf http://localhost:9090/-/ready"
check "Grafana reachable"       "curl -sf http://localhost:3001/api/health"

echo ""
echo "======================================"
echo "  PASSED: $PASS  |  FAILED: $FAIL"

if [ $FAIL -gt 0 ]; then
  echo "  ⚠️  Loop not done — fix failures before marking complete"
  exit 1
else
  echo "  🚀 All checks passed — NICE ONE BROski♾️!"
  exit 0
fi
