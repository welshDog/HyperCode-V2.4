#!/bin/bash
# Start all 12 Ghost Agents + Core stack

echo "🚀 HyperCode V2.4 - Starting Full Agent Stack"
echo "================================================"
echo ""

# docker-compose.yml pulls in every layer via `include:` (core, agents, ...).
# Never add -f for an included file (Compose merges it with itself and errors).
# The `agents` profile activates crew-orchestrator + the specialist agents.
docker compose --profile agents up -d --build

echo ""
echo "✓ Starting agents..."
echo ""
echo "Ports:"
echo "  Security Engineer        :8007"
echo "  System Architect         :8008"
echo "  Test Agent               :8080"
echo "  Throttle Agent           :8014"
echo "  Tips & Tricks Writer     :8009"
echo "  Super Hyper BROski       :8015"
echo "  Hyper Architect          :8091"
echo "  Hyper Observer           :8092"
echo "  Hyper Worker             :8093"
echo "  Hyper Split Agent        :8096"
echo "  Session Snapshot         :8097"
echo "  Agent X                  (custom)"
echo ""
echo "Check status: docker compose ps"
