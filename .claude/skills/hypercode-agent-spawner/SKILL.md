---
name: hypercode-agent-spawner
description: Spawns, configures, and registers new HyperCode agents into the Crew Orchestrator. Use when user asks to create a new agent, add a specialist to the system, or when Agent X needs to deploy a new capability. Handles agent spec creation, Docker service wiring, and Redis pub/sub registration automatically.
---

# HyperCode Agent Spawner

## Quick spawn

> **Note:** `scripts/spawn_agent.py` is not yet implemented.
> Use the manual steps below — they're fast and give you full control.

## Agent spec template

Every agent MUST have these fields in its spec JSON at `agents/<name>/agent_spec.json`:

```json
{
  "name": "agent-name",
  "role": "specialist description",
  "port": 8XXX,
  "tools": ["tool1", "tool2"],
  "memory": "redis|postgres|none",
  "safety_level": "strict|moderate|open",
  "auto_evolve": true
}
```

## Steps to spawn (manual)

1. **Create folder**: `mkdir -p agents/<name>`
2. **Write spec**: create `agents/<name>/agent_spec.json` from template above
3. **Create service**: create `agents/<name>/main.py` using the pattern in CONTRIBUTING.md
4. **Create Dockerfile**: build context must be `./agents`, dockerfile `<name>/Dockerfile`
5. **Add to compose**: add service block to `docker-compose.yml` under correct profile
6. **Register heartbeat**: add `agents:heartbeat:<name>` Redis HSET in startup (30s TTL, 10s interval)
7. **Register in Crew Orchestrator** via Redis: `r.publish('hypercode:agents:register', json.dumps(spec))`
8. **Health check**: `curl http://localhost:<port>/health`

## Available ports

Taken: 3000, 3001, 6379, 5432, 8000, 8008, 8080, 8081, 8088, 8091, 8092, 8093
Use: 8094+ for new agents

## Advanced details

**Agent Teams** (Claude Opus 4.6 style): See [AGENT_TEAMS.md](AGENT_TEAMS.md)
**Safety limits**: See [SAFETY.md](SAFETY.md)
