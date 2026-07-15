# 🔌 Hyper MCP Server v2

Spec-compliant **JSON-RPC 2.0** MCP server (Streamable HTTP) for TRAE IDE + Claude + Cursor.

Based on skills:
- HS-081 PORTAL FORGE — MCP Server + Agent Registration
- HS-129 SKILLS-OVER-MCP — SEP-2640 Resources surface

## How it actually works

Real MCP clients speak JSON-RPC 2.0 to a **single endpoint** — `POST /mcp` — not REST.
The handshake is:

```
initialize → notifications/initialized → tools/list → tools/call
```

```bash
# initialize
curl -X POST http://localhost:8765/mcp -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"trae","version":"1"}}}'

# list tools
curl -X POST http://localhost:8765/mcp -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
```

> The old `GET /tools/list` / `POST /tools/call` REST routes still exist **for curl smoke-testing only** — they are NOT the MCP surface and TRAE never uses them.

## Quick Start

```bash
cp .env.example .env          # fill in agent URLs + (for prod) MCP_API_KEY
uvicorn hyper_mcp_server:app --host 0.0.0.0 --port 8765 --reload
```

## Add to TRAE IDE

```json
{
  "name": "hyper-mcp",
  "transport": "http",
  "url": "https://hyper-sills-by-welshdog-production.up.railway.app/mcp",
  "headers": { "X-API-Key": "<your MCP_API_KEY>" }
}
```

## JSON-RPC methods

| Method | What it does |
|---|---|
| `initialize` | Handshake — returns protocol version + capabilities |
| `tools/list` | Lists registered agents as MCP tools |
| `tools/call` | Calls a tool (tool failures returned in-band as `isError`) |
| `resources/list` | SEP-2640 skills index |
| `resources/read` | Reads `skill://HS-NNN` — live body from the vault, seed fallback |
| `ping` | Liveness |
| `GET /health` | Server status (non-MCP) |

## Auth

If `MCP_API_KEY` is set, every `POST /mcp` must send `X-API-Key: <value>` or gets `401`.
Leave it blank for local dev. **Set it on the public Railway deploy.**

## Sacred Rules
- 4 spaces indent — always
- `.env` — NEVER committed
- `docker-ce-cli` — NEVER docker.io
- Redis DB1=cache, DB2=rate limits
