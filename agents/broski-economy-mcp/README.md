# BROski Economy MCP Server

MCP server exposing the BROski$ token economy as tools and resources for AI agents.

## Capabilities

### Tools

- `award_tokens(discord_id: str, amount: int, reason: str)`  
  Award BROski$ tokens to a user. Wraps the existing `award_tokens()` SQL function.

- `spend_tokens(discord_id: str, amount: int, item_slug: str)`  
  Spend BROski$ tokens on a shop item or action. Wraps `spend_tokens()`.

- `get_balance(discord_id: str)`  
  Return the current `broski_tokens` balance for a user.

### Resources

- `broski://balance/{discord_id}`  
  Read-only resource exposing a user's balance.

- `broski://transactions/{discord_id}?limit=N`  
  Read-only resource exposing recent token transactions.

## Architecture

- Runs on `agent-net` alongside other agents.
- Connects to the shared PostgreSQL database (async engine).
- Uses Docker secrets for DB credentials.
- Exposes an MCP server over stdio / HTTP (depending on deployment).

## Deployment

See `docker-compose.broski-economy-mcp.yml` in the repo root for the service definition.
