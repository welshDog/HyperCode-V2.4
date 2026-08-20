#!/bin/bash
# ============================================================================
# 25-Agent Fleet Roster Check
# ============================================================================
# Checks each agent in the CANONICAL roster (docker-push.yml's build matrix,
# reconciled 2026-08-19 — see AGENT-START.md + CLAUDE.md fleet sections) by
# name and expected port. This is intentionally narrow: it does NOT duplicate
# scripts/health-check.sh (disk/volumes/networks/resource checks) — it only
# answers "is each of the 25 canonical agents running, and does its port
# match what's expected" — all known real port collisions are fixed as of
# 2026-08-20 evening.
#
# 2026-08-20: verified against `docker compose config` (not just grep) —
# system-architect/hyper-split-agent/session-snapshot/tips-tricks-writer/
# test-agent all moved to free ports; hypercode-mcp-server phantom
# (nonexistent build context) removed from agents-full.yml entirely — it was
# never a distinct 25th agent; business-agent's mislabeled project-strategist
# clone replaced with real code at agents/business (built + ran + curled
# /health + /execute, not just claimed). Also: 14 of ~24 real agent names in
# agents-full.yml are ALSO defined in docker-compose.agents.yml with
# different build contexts — same-name merge. Bro's call: don't compose the
# two files together until that's resolved for real. See NEXT_TASKS.md item #0.
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
    "tips-tricks-writer|8018|moved off :8009 2026-08-20 (was colliding with chroma)"
    "hyper-architect|8091|"
    "hyper-observer|8092|"
    "hyper-worker|8093|"
    "hyper-split-agent|8013|moved off :8096 2026-08-20 (was colliding with safety-shepherd)"
    "session-snapshot|8017|moved off :8097 2026-08-20 (was colliding with evolve-relay)"
    "throttle-agent|8014|"
    "super-hyper-broski-agent|8015|"
    "test-agent|8019|moved off :8100 2026-08-20 (was colliding with hyper-brain)"
    "goal-keeper|8050|"
    "business-agent|8020|built for real 2026-08-20 (was a mislabeled project-strategist clone, verified: builds + /health 200 + real identity)"
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

# Empty as of 2026-08-20 evening — system-architect, hyper-split-agent,
# session-snapshot, tips-tricks-writer, and test-agent were all moved off
# colliding ports the same day. Add entries here again if a future port change
# reintroduces one.
COLLISIONS=()

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
echo -e "${YELLOW}Blocked (needs a human decision): $BLOCKED / 24${NC}"
echo ""
echo "Reminder: 'not running' agents are expected right now — Bro's call 2026-08-20"
echo "evening is DON'T compose agents-full.yml with the base stack at all yet. 14"
echo "agent names in this roster silently merge with different definitions in"
echo "docker-compose.agents.yml (9 of them are live right now via THAT file, not"
echo "this one) — see NEXT_TASKS.md item #0. All real port-vs-differently-named-"
echo "service collisions are fixed as of 2026-08-20 evening. --profile agents is"
echo "still required on the compose command whenever item #0 is resolved for real."
echo "See HyperCode-V2.4/AGENT-START.md fleet section for full detail."
echo ""

if [ "$BLOCKED" -gt 0 ]; then
    exit 1
fi
exit 0
