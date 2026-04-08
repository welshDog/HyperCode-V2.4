# 🤖 AI Agent Orchestration — HyperCode V2.0

## Agent Directory Map

| Directory | Contents |
|---|---|
| `agents/` | Core agent definitions |
| `Hyper-Agents-Box/` | Agent sandbox & experiments |
| `broski-business-agents/` | Business automation agents |
| `hyper-mission-system/` | Mission/quest gamification |
| `mcp/` | MCP server implementations |

## Agent Lifecycle

```
Spawn → Register → Health Check → Execute Task → Report → Idle/Kill
         ↑                                              |
         └──────────── Healer Agent auto-restarts ──────┘
```

## MCP Integration

The `.mcp.json` config connects Claude to HyperCode's MCP server:

```json
{
  "mcpServers": {
    "hypercode": {
      "command": "...",
      "args": [...]
    }
  }
}
```

Available MCP tools:
- `hypercode_system_health` — full system status
- `hypercode_agent_system_health` — per-agent health
- `hypercode_list_agents` — all registered agents
- `hypercode_list_tasks` — active task queue

## Swarm Test

```bash
# Run agent swarm test
python scripts/run_swarm_test.py

# Run NemoClaw agent
python scripts/run_nemoclaw.py

# Use agents via API
python scripts/use_agents.py
```

## Agent X — Meta-Architect Pattern

Agent X autonomously:
1. Analyses task requirements
2. Designs a new agent spec
3. Generates the agent code
4. Builds a Docker image via Docker Model Runner
5. Deploys into the Compose network
6. Registers with Crew Orchestrator
7. Monitors via Healer Agent

This is the **Evolutionary Pipeline** — agents rebuild themselves.

## Healer Agent Pattern

```python
# Healer monitors all services on port 8008
# On failure detection:
# 1. Logs the failure with timestamp
# 2. Attempts restart (docker restart <container>)
# 3. Publishes event to Redis channel: hypercode:healer:events
# 4. Updates Prometheus metric: hypercode_service_restarts_total
# 5. Sends alert if restart count exceeds threshold
```

## CREWai-style Task Delegation

```python
# Crew Orchestrator (port 8081) handles task assignment
POST /tasks/assign
{
  "task": "analyze_codebase",
  "target_agent": "agent_x",
  "priority": 8,
  "payload": {"repo": "welshDog/HyperCode-V2.0"}
}
```
