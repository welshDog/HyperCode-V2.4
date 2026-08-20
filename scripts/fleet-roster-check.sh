#!/bin/bash
# ============================================================================
# 25-Agent Fleet Roster Check
# ============================================================================
# Checks each agent in the CANONICAL roster (docker-push.yml's build matrix,
# reconciled 2026-08-19 — see AGENT-START.md + CLAUDE.md fleet sections) by
# name and expected port. This is intentionally narrow: it does NOT duplicate
# scripts/health-check.sh (disk/volumes/networks/resource checks) — it only
# answers "is each of the 25 canonical agents running, and does its port
# match what's expected, including the 2 remaining known collisions".
#
# 2026-08-20: verified against `docker compose config` (not just grep) —
# system-architect/hyper-split-agent/session-snapshot moved to free ports;
# hypercode-mcp-server phantom (nonexistent build context) removed from
# agents-full.yml entirely — it was never a distinct 25th agent. New finding:
# tips-tricks-writer collides with live `chroma` :8009 (missed 08-19). Also:
# 14 of ~24 real agent names in agents-full.yml are ALSO defined in
# docker-compose.agents.yml with different build contexts — same-name merge,
# unaudited, likely deploys a hybrid of both definitions for most agents.
# See NEXT_TASKS.md P1 "agents-full.yml name-collision audit".
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
    "system-architect|8010|moved off :8008 2026-08-20 (was colliding with healer-agent)"
    "project-strategist|8001|"
    "tips-tricks-writer|8009|KNOWN COLLISION: chroma already binds :8009 — found 2026-08-20, not yet fixed"
    "hyper-architect|8091|"
    "hyper-observer|8092|"
    "hyper-worker|8093|"
    "hyper-split-agent|8013|moved off :8096 2026-08-20 (was colliding with safety-shepherd)"
    "session-snapshot|8017|moved off :8097 2026-08-20 (was colliding with evolve-relay)"
    "throttle-agent|8014|"
    "super-hyper-broski-agent|8015|"
    "test-agent|8100|KNOWN COLLISION: hyper-brain already binds :8100"
    "goal-keeper|8050|"
    "business-agent|-|BLOCKED: no Dockerfile exists at any sensible path — needs a human decision, not a build"
    "coderabbit-webhook|8024|"
)
# hypercode-mcp-server intentionally not in this roster: it is the real, live
# MCP gateway defined in docker-compose.agents.yml (:8823), not a distinct 25th
# agent. A phantom duplicate of it in agents-full.yml (pointing at a build
# context that doesn't exist) was removed 2026-08-20 — see that file's header.

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
    "tips-tricks-writer:8009|chroma"
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

echo "Live now:            $LIVE / 24"
echo "Built, not running:  $BUILT_NOT_RUNNING / 24"
echo -e "${YELLOW}Blocked (no valid build path): $BLOCKED / 24${NC}"
echo ""
echo "Reminder: 'not running' agents are expected right now — nobody has decided"
echo "to bring up agents-full.yml yet, and 2 of the missing agents (tips-tricks-writer,"
echo "test-agent) would still fail to bind against live services if you tried. Fix"
echo "those before launching. Also: launching for real requires --profile agents on"
echo "the compose command (see agents-full.yml header) and 14 agent names in this"
echo "roster are unaudited same-name merges against docker-compose.agents.yml — see"
echo "NEXT_TASKS.md P1. See HyperCode-V2.4/AGENT-START.md fleet section for full detail."
echo ""

if [ "$BLOCKED" -gt 0 ]; then
    exit 1
fi
exit 0
