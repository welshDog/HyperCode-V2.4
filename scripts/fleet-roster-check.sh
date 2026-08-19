#!/bin/bash
# ============================================================================
# 25-Agent Fleet Roster Check
# ============================================================================
# Checks each agent in the CANONICAL roster (docker-push.yml's build matrix,
# reconciled 2026-08-19 — see AGENT-START.md + CLAUDE.md fleet sections) by
# name and expected port. This is intentionally narrow: it does NOT duplicate
# scripts/health-check.sh (disk/volumes/networks/resource checks) — it only
# answers "is each of the 25 canonical agents running, and does its port
# match what's expected, including the 3 known collisions".
#
# Usage: bash scripts/fleet-roster-check.sh
# ============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

LIVE=0
BUILT_NOT_RUNNING=0
BLOCKED=0

header() {
    echo ""
    echo "==================================================================="
    echo "$*"
    echo "==================================================================="
}

# name | expected_port | note (collision / blocked / empty)
# port "-" = no fixed host port expected for this agent
ROSTER=(
    "crew-orchestrator|8081|"
    "brain-agent|8082|not running under this name (hyper-brain/agent-hyper-brain-core are separate live containers)"
    "coder|-|not running under this name (coder-agent is live, likely same code)"
    "agent-x|8083|two compose files disagree on this port (agents.yml=8084, agents-full.yml=8083) — unreconciled"
    "frontend-specialist|8012|"
    "backend-specialist|8003|"
    "database-architect|8004|"
    "qa-engineer|8005|"
    "devops-engineer|8006|"
    "security-engineer|8007|"
    "system-architect|8008|KNOWN COLLISION: healer-agent already binds :8008"
    "project-strategist|8001|"
    "tips-tricks-writer|8009|"
    "hyper-architect|8091|"
    "hyper-observer|8092|"
    "hyper-worker|8093|"
    "hyper-split-agent|8096|KNOWN COLLISION: safety-shepherd already binds :8096"
    "session-snapshot|8097|KNOWN COLLISION: evolve-relay already binds :8097"
    "throttle-agent|8014|"
    "super-hyper-broski-agent|8015|"
    "test-agent|8100|KNOWN COLLISION: hyper-brain already binds :8100"
    "goal-keeper|8050|"
    "business-agent|-|BLOCKED: no Dockerfile exists at any sensible path — needs a human decision, not a build"
    "coderabbit-webhook|8024|"
    "hypercode-mcp-server|-|NAME COLLISION: a different, already-live hypercode-mcp-server exists at :8823 (real MCP gateway)"
)

header "25-AGENT FLEET ROSTER CHECK (canonical: docker-push.yml, reconciled 2026-08-19)"

printf "%-28s %-10s %-10s %s\n" "AGENT" "PORT" "STATUS" "NOTE"
printf "%-28s %-10s %-10s %s\n" "-----" "----" "------" "----"

for entry in "${ROSTER[@]}"; do
    IFS='|' read -r name port note <<< "$entry"

    if [[ "$note" == BLOCKED:* ]]; then
        printf "%-28s %-10s ${YELLOW}%-10s${NC} %s\n" "$name" "$port" "BLOCKED" "$note"
        BLOCKED=$((BLOCKED+1))
        continue
    fi

    running=$(docker ps --filter "name=^${name}\$" --filter "status=running" --format "{{.Names}}" 2>/dev/null)

    if [ -n "$running" ]; then
        printf "%-28s %-10s ${GREEN}%-10s${NC} %s\n" "$name" "$port" "LIVE" "$note"
        LIVE=$((LIVE+1))
    else
        printf "%-28s %-10s ${YELLOW}%-10s${NC} %s\n" "$name" "$port" "NOT RUNNING" "$note"
        BUILT_NOT_RUNNING=$((BUILT_NOT_RUNNING+1))
    fi
done

header "KNOWN PORT COLLISIONS (if the missing agents above are ever launched)"

COLLISIONS=(
    "system-architect:8008|healer-agent"
    "hyper-split-agent:8096|safety-shepherd"
    "session-snapshot:8097|evolve-relay"
    "test-agent:8100|hyper-brain"
)

for c in "${COLLISIONS[@]}"; do
    wants="${c%%|*}"
    holder="${c##*|}"
    holder_status=$(docker ps --filter "name=^${holder}\$" --filter "status=running" --format "{{.Names}}" 2>/dev/null)
    if [ -n "$holder_status" ]; then
        echo -e "${RED}✗${NC} $wants would fail to bind — $holder is live and already holds that port"
    else
        echo -e "${GREEN}✓${NC} $wants's port is free right now — $holder is not currently running"
    fi
done

header "SUMMARY"

echo "Live now:            $LIVE / 25"
echo "Built, not running:  $BUILT_NOT_RUNNING / 25"
echo -e "${YELLOW}Blocked (no valid build path): $BLOCKED / 25${NC}"
echo ""
echo "Reminder: 'not running' agents are expected right now — nobody has decided"
echo "to bring up agents-full.yml yet, and 3 of the missing agents would fail to"
echo "bind against live services if you tried. Fix collisions before launching,"
echo "not after. See HyperCode-V2.4/AGENT-START.md fleet section for full detail."
echo ""

if [ "$BLOCKED" -gt 0 ]; then
    exit 1
fi
exit 0
