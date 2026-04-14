#!/usr/bin/env bash
# scripts/trivy-pre-push.sh
# ─────────────────────────────────────────────────────────────────────────────
# HyperCode Phase 8 — Trivy pre-push hook
# Blocks git push if any changed Dockerfile produces a CRITICAL CVE.
#
# Install:
#   cp scripts/trivy-pre-push.sh .git/hooks/pre-push
#   chmod +x .git/hooks/pre-push
#
# Requirements: docker + trivy installed locally (or run via Docker)
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

BOLD="\033[1m"
RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
RESET="\033[0m"

# Agents that need the repo root as build context (they reference root-relative paths)
ROOT_CONTEXT_AGENTS=(
  "agent-x"
  "healer"
  "hyper-agents/architect"
  "hyper-agents/observer"
  "hyper-agents/worker"
  "05-devops-engineer"
)

needs_root_context() {
  local agent="$1"
  for ra in "${ROOT_CONTEXT_AGENTS[@]}"; do
    [[ "$agent" == "$ra" ]] && return 0
  done
  return 1
}

# ── Detect Trivy ─────────────────────────────────────────────────────────────
TRIVY_CMD=""
if command -v trivy &>/dev/null; then
  TRIVY_CMD="trivy"
elif docker image inspect aquasec/trivy:latest &>/dev/null 2>&1; then
  TRIVY_CMD="docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest"
else
  echo -e "${YELLOW}⚠️  Trivy not found locally or as Docker image — skipping pre-push scan.${RESET}"
  echo "   Install: https://aquasecurity.github.io/trivy/latest/getting-started/installation/"
  exit 0
fi

# ── Find changed Dockerfiles ──────────────────────────────────────────────────
CHANGED=$(git diff --name-only HEAD~1 HEAD 2>/dev/null | grep -E '(^|/)Dockerfile$' || true)

if [[ -z "$CHANGED" ]]; then
  # Also check staged (for first commit or force-push scenarios)
  CHANGED=$(git diff --cached --name-only | grep -E '(^|/)Dockerfile$' || true)
fi

if [[ -z "$CHANGED" ]]; then
  echo -e "${GREEN}✅ No Dockerfiles changed — skipping Trivy scan.${RESET}"
  exit 0
fi

echo -e "${BOLD}🔒 HyperCode Trivy pre-push scan${RESET}"
echo "Changed Dockerfiles:"
echo "$CHANGED" | sed 's/^/  /'
echo ""

FAILED=0

while IFS= read -r dockerfile; do
  [[ -z "$dockerfile" ]] && continue
  [[ ! -f "$dockerfile" ]] && continue

  # Derive agent name from path (e.g. agents/agent-x/Dockerfile → agent-x)
  dir=$(dirname "$dockerfile")
  # Strip leading agents/ prefix for display
  agent=$(echo "$dir" | sed 's|^agents/||')
  image="hypercode-prepush-$(echo "$agent" | tr '/' '-'):check"

  echo -e "${BOLD}🔍 Building $agent...${RESET}"

  # Choose build context
  if needs_root_context "$agent"; then
    docker build -f "$dockerfile" -t "$image" . 2>&1 | tail -5
  else
    docker build -f "$dockerfile" -t "$image" "$dir" 2>&1 | tail -5
  fi

  echo "🔍 Scanning $agent for CRITICAL CVEs..."

  set +e
  $TRIVY_CMD image \
    --scanners vuln \
    --severity CRITICAL \
    --exit-code 1 \
    --quiet \
    "$image"
  scan_exit=$?
  set -e

  if [[ $scan_exit -ne 0 ]]; then
    echo -e "${RED}🔴 CRITICAL CVEs found in $agent — push blocked!${RESET}"
    FAILED=1
  else
    echo -e "${GREEN}✅ $agent — clean${RESET}"
  fi

  # Clean up image
  docker rmi "$image" &>/dev/null || true
  echo ""

done <<< "$CHANGED"

if [[ $FAILED -eq 1 ]]; then
  echo -e "${RED}${BOLD}🚨 Push blocked — fix all CRITICAL CVEs before pushing.${RESET}"
  echo ""
  echo "Tips:"
  echo "  • Add 'RUN apt-get update && apt-get upgrade -y' after FROM in your Dockerfile"
  echo "  • Bump pip: 'RUN pip install --upgrade pip==26.0.1 setuptools>=80.0.0 wheel==0.46.2'"
  echo "  • Run locally: make scan-agent AGENT=<name>"
  exit 1
fi

echo -e "${GREEN}${BOLD}✅ All Trivy scans passed — pushing!${RESET}"
exit 0
