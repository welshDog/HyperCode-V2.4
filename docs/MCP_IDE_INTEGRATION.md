# HyperCode MCP Server — AI IDE Integration Guide

The `hypercode-mcp-server` exposes HyperCode's core capabilities as MCP tools.
Any MCP-compatible AI IDE can connect and use the stack natively.

**Port:** `8823` (SSE transport)
**SSE URL:** `http://localhost:8823/sse`

---

## Available Tools

| Tool | Description |
|------|-------------|
| `hypercode_system_health` | Overall stack health — first thing to call |
| `hypercode_list_agents` | All running agents, status, XP, level, coins |
| `hypercode_agent_system_health` | Deep CPU/memory/Redis metrics from orchestrator |
| `hypercode_list_tasks` | List tasks, filterable by status |
| `hypercode_create_task` | Create a new task with priority + optional agent assignment |
| `hypercode_generate_plan` | Run the planning pipeline on any PRD/issue/doc |
| `hypercode_get_logs` | Recent log entries from all agents |
| `hypercode_broski_wallet` | BROski$ balance, level, XP |
| `hypercode_broski_leaderboard` | Top agents by coins + level |
| `hypercode_execute_agent` | Send a command to the crew orchestrator |

---

## Claude Code

The `.mcp.json` file in the project root is automatically picked up by Claude Code
when you open the project. No extra configuration needed.

If you need to add it manually (`~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "hypercode": {
      "type": "sse",
      "url": "http://localhost:8823/sse"
    }
  }
}
```

---

## Cursor

In Cursor settings → MCP → Add server:
```
Name: HyperCode
Transport: SSE
URL: http://localhost:8823/sse
```

---

## Windsurf / Codeium

In `~/.codeium/windsurf/mcp_config.json`:
```json
{
  "mcpServers": {
    "hypercode": {
      "serverUrl": "http://localhost:8823/sse"
    }
  }
}
```

---

## Start the server

```bash
# Already in the main docker-compose — starts automatically
docker compose up -d hypercode-mcp-server

# Check it's running
curl http://localhost:8823/sse
```

---

## Example Usage (from Claude Code)

Once connected, you can ask Claude Code:

- *"Check the HyperCode agent status"* → calls `hypercode_list_agents`
- *"Generate an implementation plan for this PRD: ..."* → calls `hypercode_generate_plan`
- *"What errors are in the logs?"* → calls `hypercode_get_logs`
- *"Create a task: fix the healer agent import bug"* → calls `hypercode_create_task`
- *"What's the BROski leaderboard?"* → calls `hypercode_broski_leaderboard`
