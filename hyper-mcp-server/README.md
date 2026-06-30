# 🔌 Hyper MCP Server

FastAPI MCP server for TRAE IDE + Claude + Cursor.

Based on skills:
- HS-081 PORTAL FORGE — MCP Server + Agent Registration
- HS-129 SKILLS-OVER-MCP — SEP-2640 Resources surface

## Quick Start

```bash
cp .env.example .env
# fill in your agent URLs
uvicorn hyper_mcp_server:app --host 0.0.0.0 --port 8765 --reload
```

## Add to TRAE IDE

```json
{
  "name": "hyper-mcp",
  "transport": "http",
  "url": "http://localhost:8765"
}
```

## Endpoints

| Endpoint | What it does |
|---|---|
| GET `/tools/list` | Lists all registered agents as MCP tools |
| POST `/tools/call` | Calls a specific agent tool |
| GET `/resources/list` | SEP-2640 skills index |
| GET `/resources/read?uri=skill://HS-081` | Read one skill |
| GET `/health` | Server status |

## Sacred Rules
- 4 spaces indent — always
- .env — NEVER committed
- docker-ce-cli — NEVER docker.io
- Redis DB1=cache, DB2=rate limits
