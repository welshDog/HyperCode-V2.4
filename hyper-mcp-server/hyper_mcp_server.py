"""
Hyper MCP Server v2 — spec-compliant JSON-RPC 2.0 over Streamable HTTP.

Single transport endpoint: POST /mcp  (JSON-RPC 2.0)
Real MCP clients (TRAE, Claude, Cursor) handshake here:
    initialize → notifications/initialized → tools/list → tools/call

Legacy REST routes (/tools/list, /tools/call, /resources/*) are kept ONLY
for curl smoke-testing — they are NOT the MCP surface and TRAE never uses them.
"""

from fastapi import FastAPI, Request, Header
from fastapi.responses import JSONResponse, Response
from typing import Any
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Hyper MCP Server", version="2.0.0")

# ── Config (from .env — NEVER hardcoded) ───────────────────
BROSKI_AGENT_URL = os.getenv("BROSKI_AGENT_URL", "http://localhost:8001")
BRAIN_CORE_URL   = os.getenv("BRAIN_CORE_URL",   "http://localhost:8002")
SKILLS_API_URL   = os.getenv("SKILLS_API_URL",   "http://localhost:8003")

# Optional auth — if MCP_API_KEY is set, every /mcp call must send X-API-Key.
# Left unset (local dev) = open, so smoke tests still work.
MCP_API_KEY = os.getenv("MCP_API_KEY", "").strip()

# Protocol version we speak. We echo the client's if they send a known one.
DEFAULT_PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_PROTOCOL_VERSIONS = {"2024-11-05", "2025-03-26", "2025-06-18"}

SERVER_INFO = {"name": "hyper-mcp-server", "version": "2.0.0"}

# ── JSON-RPC error codes ───────────────────────────────────
PARSE_ERROR      = -32700
INVALID_REQUEST  = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS   = -32602
INTERNAL_ERROR   = -32603

# ── Tool Registry ──────────────────────────────────────────
TOOLS = [
    {
        "name": "broski_agent",
        "description": "BROski orchestrator — tasks, Discord events, BROski$ rewards.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Task to run"}
            },
            "required": ["task"],
        },
    },
    {
        "name": "brain_core_agent",
        "description": "Hyper Brain Core — memory, context, second brain queries.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to look up"}
            },
            "required": ["query"],
        },
    },
    {
        "name": "hyper_skill_agent",
        "description": "Load and execute a HYPER-SILLs skill by ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "skill_id": {"type": "string", "description": "e.g. HS-081"}
            },
            "required": ["skill_id"],
        },
    },
]

# ── Skills-Over-MCP Resources (SEP-2640) ───────────────────
# NOTE: static seed list. resources/read fetches the live skill body from
# SKILLS_API_URL when reachable, falling back to this metadata.
SKILLS_INDEX = [
    {"uri": "skill://HS-081", "id": "HS-081", "name": "PORTAL FORGE",     "mimeType": "text/markdown", "description": "MCP Server + Agent Registration Pattern"},
    {"uri": "skill://HS-129", "id": "HS-129", "name": "SKILLS-OVER-MCP",  "mimeType": "text/markdown", "description": "Expose Skills as MCP Resources (SEP-2640)"},
    {"uri": "skill://HS-018", "id": "HS-018", "name": "BRIDGE KEEPER",    "mimeType": "text/markdown", "description": "MCP Bridge Manifest"},
    {"uri": "skill://HS-017", "id": "HS-017", "name": "MIND CORE",        "mimeType": "text/markdown", "description": "Hyper Brain Core Manifest"},
]


# ── Tool execution (shared by MCP + legacy REST) ───────────
async def _run_tool(name: str, arguments: dict[str, Any]) -> str:
    async with httpx.AsyncClient(timeout=15.0) as client:
        if name == "broski_agent":
            resp = await client.post(
                f"{BROSKI_AGENT_URL}/run", json={"task": arguments.get("task")}
            )
            return resp.json().get("result", "No response from BROski agent")

        if name == "brain_core_agent":
            resp = await client.post(
                f"{BRAIN_CORE_URL}/query", json={"query": arguments.get("query")}
            )
            return resp.json().get("answer", "No response from Brain Core")

        if name == "hyper_skill_agent":
            resp = await client.get(
                f"{SKILLS_API_URL}/skill/{arguments.get('skill_id')}"
            )
            return resp.json().get("content", "Skill not found")

        raise KeyError(name)


async def _read_skill(skill_id: str) -> dict[str, Any]:
    """Resolve a skill resource — try the live vault, fall back to seed metadata."""
    uri = f"skill://{skill_id}"
    match = next((s for s in SKILLS_INDEX if s["id"] == skill_id), None)
    # Try live body from the vault API.
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{SKILLS_API_URL}/skill/{skill_id}")
            if resp.status_code == 200:
                body = resp.json().get("content")
                if body:
                    return {"uri": uri, "mimeType": "text/markdown", "text": body}
    except httpx.HTTPError:
        pass  # vault unreachable — fall through to seed metadata
    if match:
        text = (
            f"# {match['name']} ({skill_id})\n\n{match['description']}\n\n"
            f"_Live body unavailable — showing seed metadata._"
        )
        return {"uri": uri, "mimeType": "text/markdown", "text": text}
    return {
        "uri": uri,
        "mimeType": "text/plain",
        "text": f"⚠️ Skill {skill_id} not found. Use resources/list to browse.",
    }


# ── JSON-RPC dispatch ──────────────────────────────────────
async def _dispatch(method: str, params: dict[str, Any]) -> dict[str, Any]:
    """Return the JSON-RPC `result` object for a method, or raise _RpcError."""
    if method == "initialize":
        client_proto = params.get("protocolVersion")
        proto = client_proto if client_proto in SUPPORTED_PROTOCOL_VERSIONS else DEFAULT_PROTOCOL_VERSION
        return {
            "protocolVersion": proto,
            "capabilities": {
                "tools": {"listChanged": False},
                "resources": {"listChanged": False, "subscribe": False},
            },
            "serverInfo": SERVER_INFO,
        }

    if method == "ping":
        return {}

    if method == "tools/list":
        return {"tools": TOOLS}

    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        if not name:
            raise _RpcError(INVALID_PARAMS, "Missing tool name")
        try:
            text = await _run_tool(name, arguments)
        except KeyError:
            raise _RpcError(INVALID_PARAMS, f"Unknown tool: {name}")
        except httpx.HTTPError as exc:
            # Tool errors are reported in-band (isError), not as protocol errors.
            return {
                "content": [{"type": "text", "text": f"Tool '{name}' failed: {exc}"}],
                "isError": True,
            }
        return {"content": [{"type": "text", "text": text}], "isError": False}

    if method == "resources/list":
        return {"resources": SKILLS_INDEX}

    if method == "resources/read":
        uri = params.get("uri", "")
        if not uri.startswith("skill://"):
            raise _RpcError(INVALID_PARAMS, f"Unsupported resource uri: {uri}")
        skill_id = uri.replace("skill://", "")
        return {"contents": [await _read_skill(skill_id)]}

    raise _RpcError(METHOD_NOT_FOUND, f"Method not found: {method}")


class _RpcError(Exception):
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def _error(req_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


# ── MCP transport endpoint (Streamable HTTP, JSON-RPC 2.0) ──
@app.post("/mcp")
async def mcp_endpoint(request: Request, x_api_key: str | None = Header(default=None)):
    # Auth gate (only enforced when MCP_API_KEY is configured).
    if MCP_API_KEY and x_api_key != MCP_API_KEY:
        return JSONResponse(
            _error(None, INVALID_REQUEST, "Unauthorized: bad or missing X-API-Key"),
            status_code=401,
        )

    try:
        payload = await request.json()
    except Exception:
        return JSONResponse(_error(None, PARSE_ERROR, "Parse error"), status_code=400)

    # Batch requests.
    if isinstance(payload, list):
        responses = []
        for msg in payload:
            resp = await _handle_message(msg)
            if resp is not None:
                responses.append(resp)
        if not responses:
            return Response(status_code=202)  # all notifications
        return JSONResponse(responses)

    resp = await _handle_message(payload)
    if resp is None:
        return Response(status_code=202)  # notification — no body
    return JSONResponse(resp)


async def _handle_message(msg: Any) -> dict[str, Any] | None:
    """Handle one JSON-RPC message. Returns None for notifications (no id)."""
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
        return _error(None, INVALID_REQUEST, "Invalid JSON-RPC 2.0 request")

    req_id = msg.get("id")
    method = msg.get("method")
    params = msg.get("params") or {}

    # Notifications have no id and expect no response.
    is_notification = "id" not in msg
    if method is None:
        return None if is_notification else _error(req_id, INVALID_REQUEST, "Missing method")

    # notifications/initialized and other client notifications: ack silently.
    if is_notification:
        return None

    try:
        result = await _dispatch(method, params)
    except _RpcError as exc:
        return _error(req_id, exc.code, exc.message)
    except Exception as exc:  # noqa: BLE001 — surface as JSON-RPC internal error
        return _error(req_id, INTERNAL_ERROR, f"Internal error: {exc}")

    return {"jsonrpc": "2.0", "id": req_id, "result": result}


# ── Legacy REST (curl smoke-testing ONLY — not the MCP surface) ──
@app.get("/tools/list")
async def rest_tools_list():
    return {"tools": TOOLS}


@app.post("/tools/call")
async def rest_tools_call(req: Request):
    body = await req.json()
    name = body.get("name")
    arguments = body.get("arguments") or {}
    try:
        text = await _run_tool(name, arguments)
    except KeyError:
        return {"error": f"Unknown tool: {name}"}
    return {"content": [{"type": "text", "text": text}]}


@app.get("/resources/list")
async def rest_resources_list():
    return {"resources": SKILLS_INDEX}


@app.get("/resources/read")
async def rest_resources_read(uri: str):
    skill_id = uri.replace("skill://", "")
    return {"contents": [await _read_skill(skill_id)]}


# ── Health ─────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status": "online",
        "server": "Hyper MCP v2",
        "transport": "json-rpc-2.0 /mcp",
        "protocol_version": DEFAULT_PROTOCOL_VERSION,
        "auth": "enabled" if MCP_API_KEY else "open",
        "tools": [t["name"] for t in TOOLS],
        "sep_2640": "tracking",
    }
