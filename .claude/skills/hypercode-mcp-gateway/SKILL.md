---
name: hypercode-mcp-gateway
description: Configures and manages the HyperCode MCP (Model Context Protocol) gateway that connects Claude and other AI models to HyperCode services. Use when adding new MCP tools, debugging MCP connections, registering new servers, or wiring external services like GitHub, Slack, or databases into the agent ecosystem.
---

# HyperCode MCP Gateway

## MCP server registry

Config lives in: `.mcp.json`

### Currently registered (live)

```json
{
  "mcpServers": {
    "hypercode": {
      "type": "sse",
      "url": "http://localhost:8823/sse",
      "description": "HyperCode AI agent stack — manage agents, tasks, plans, logs and BROski$ economy"
    }
  }
}
```

### Planned (not yet registered — add when ready)

```json
{
  "mcpServers": {
    "HyperCode:github": { "command": "npx", "args": ["-y", "@modelcontextprotocol/server-github"] },
    "HyperCode:filesystem": { "command": "npx", "args": ["-y", "@modelcontextprotocol/server-filesystem", "/"] },
    "HyperCode:redis": { "command": "python", "args": ["mcp/redis_server.py"] }
  }
}
```

## Add new MCP server

1. Add entry to `.mcp.json`
2. Restart Claude Code session
3. Verify with: `HyperCode:<server>:list_tools`

## Tool naming (CRITICAL)

ALWAYS use fully qualified names in Skills:
```
HyperCode:github:create_issue    ✅
create_issue                     ❌  (ambiguous)
```

## Key MCP tools available

| Server | Status | Key Tools |
|--------|--------|-----------|
| `hypercode` | **Live** | `hypercode_list_agents`, `hypercode_create_task`, `hypercode_system_health`, `hypercode_broski_wallet` |
| `HyperCode:github` | Planned | `create_issue`, `create_pr`, `get_file` |
| `HyperCode:filesystem` | Planned | `read_file`, `write_file`, `list_dir` |
| `HyperCode:redis` | Planned | `publish`, `subscribe`, `get`, `set` |

For full tool list: See [TOOLS.md](TOOLS.md)
