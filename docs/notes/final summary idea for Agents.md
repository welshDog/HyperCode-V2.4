a final summary for you:

Fixed 1 — Healer Agent Watchlist: Added HEALER_WATCHED_SERVICES env var to docker-compose.yml (line ~1142). Healer now only monitors core services (hypercode-core, redis, postgres, celery-worker, hypercode-ollama, healer-agent) instead of watching non-existent specialist agents.

Fixed 2 — Lean Agent Stack: Created docker-compose.agents-lite.yml override file. Starts only 4 essential agents (crew-orchestrator, coder-agent, tips-tricks-writer, healer-agent) with 512M RAM limits each. Total footprint ~2GB—fits in 4GB systems. Specialist agents can be spawned on-demand.

Fixed 3 — Agent Factory: Created agents/agent-factory/ with:

spawn_agent.sh — One-command agent spawner (5.8 KB)
README.md — Complete usage guide (7.4 KB)
Files Created/Modified:

✏️ docker-compose.yml — Added HEALER_WATCHED_SERVICES env var
✨ docker-compose.agents-lite.yml — Lean profile override
✨ agents/agent-factory/spawn_agent.sh — Agent spawner script
✨ agents/agent-factory/README.md — Factory documentation
🔄 agents/README.md — Updated with quick-start paths
✨ AGENT_INFRASTRUCTURE_FIX.md — Complete fix documentation
✨ AGENT_INFRASTRUCTURE_QUICK_REFERENCE.sh — Visual reference
Quick Start:

# 4GB systems
cd HyperCode-V2.0
docker compose -f docker-compose.yml -f docker-compose.agents-lite.yml up -d

# Spawn agents on-demand
cd agents/agent-factory
./spawn_agent.sh coder-agent
./spawn_agent.sh healer-agent
All success criteria met. Agent infrastructure is now robust, efficient, and user-friendly! 🚀
