# BROski Economy MCP Server

This doc covers how to run and test the BROski Economy MCP server, which exposes the BROski$ token economy as MCP tools and resources.

## Overview

The server provides:

### Tools

- `award_tokens(discord_id, amount, reason)` — Award BROski$ to a user.
- `spend_tokens(discord_id, amount, item_slug)` — Spend BROski$ on an item.
- `get_balance(discord_id)` — Get a user's token balance.

### Resources

- `broski://balance/{discord_id}` — Read-only balance resource.
- `broski://transactions/{discord_id}?limit=N` — Recent transactions.

This follows the Model Context Protocol (MCP) pattern: tools, resources, and prompts exposed over a standard interface.[web:16][web:19][web:25]

## Running the Server

### 1. Ensure secrets exist

You need a `secrets/database_url.txt` file with your Postgres URL (same pattern as other services):

```bash
# From HyperCode-V2.4 root
echo "postgresql://user:pass@postgres:5432/hypercode" > secrets/database_url.txt
```

Adjust host/user/pass/db to match your environment.

### 2. Start the service

Include the new compose file when starting the stack:

```powershell
docker compose `
  -f docker-compose.yml `
  -f docker-compose.secrets.yml `
  -f docker-compose.broski-economy-mcp.yml `
  up -d broski-economy-mcp
```

Or add `broski-economy-mcp` to your existing `docker compose up -d` command.

### 3. Verify health

```powershell
curl http://localhost:8099/health
```

Expected: `{"status":"ok"}`

### 4. Check MCP discovery

```powershell
curl http://localhost:8099/.well-known/mcp
```

Expected: JSON with `tools` and `resources` matching the definitions in `server.py`.

## Testing Tools

### Get balance

```powershell
curl -X POST http://localhost:8099/mcp/tools/get_balance `
  -H "Content-Type: application/json" `
  -d '{"discord_id": "123456789012345678"}'
```

### Award tokens

```powershell
curl -X POST http://localhost:8099/mcp/tools/award_tokens `
  -H "Content-Type: application/json" `
  -d '{"discord_id": "123456789012345678", "amount": 50, "reason": "Completed lesson 1"}'
```

### Spend tokens

```powershell
curl -X POST http://localhost:8099/mcp/tools/spend_tokens `
  -H "Content-Type: application/json" `
  -d '{"discord_id": "123456789012345678", "amount": 100, "item_slug": "agent-sandbox-access"}'
```

## Testing Resources

### Balance resource

```powershell
curl "http://localhost:8099/mcp/resources/broski://balance/123456789012345678"
```

### Transactions resource

```powershell
curl "http://localhost:8099/mcp/resources/broski://transactions/123456789012345678?limit=5"
```

## Integrating with Agents

To use this from your existing agents:

1. Have the agent call `GET /.well-known/mcp` to discover available tools.
2. When the agent needs to award/spend/check tokens, it POSTs to `/mcp/tools/{tool_name}` with the appropriate JSON body.
3. For read-only views, agents can GET the `broski://...` resource URLs.

Later, you can wire this into MCP clients (Claude Desktop, VS Code, Cursor) by configuring them to point at this server's endpoint.

## Observability

- Logs: `docker logs broski-economy-mcp`
- Metrics: integrate with Prometheus via `/metrics` in a future iteration.
- Traces: add OpenTelemetry OTLP export to align with HyperCode's existing tracing.

## Security Notes

- The server runs as non-root (`appuser`) following Phase 9 patterns.
- It uses the shared `DATABASE_URL` secret; ensure DB user has appropriate permissions for `award_tokens` / `spend_tokens` functions.
- Rate limiting and auth can be added at the API gateway / ingress layer if exposed externally.

## Next Steps

Future iterations can:

- Add OpenTelemetry tracing (OTLP) to match HyperCode core.
- Add a `/metrics` endpoint for Prometheus.
- Wrap this server with an official MCP SDK implementation for broader client compatibility.
- Extend with more resources (e.g., shop items, referral stats).
