"""mcp-rest-adapter — thin REST shim in front of the MCP gateway.

Transport: MCP **Streamable HTTP** (spec 2025-03-26 / 2025-06-18).
Older revisions of this file spoke the legacy HTTP+SSE transport
(GET /sse -> `event: endpoint` -> POST to a session URL). The current
`docker/mcp-gateway` image dropped that — it serves a single endpoint
(`/mcp`) where the client POSTs JSON-RPC and the response comes back
inline as either `application/json` or a short `text/event-stream`.

Handshake per call:
  1. POST `initialize`            -> response carries the `Mcp-Session-Id` header
  2. POST `notifications/initialized` (best effort, with the session header)
  3. POST the real method         (`tools/list` / `tools/call`)
  4. DELETE the session           (best effort cleanup)
"""

import hmac
import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

GATEWAY_BASE = os.getenv("MCP_GATEWAY_BASE_URL", "http://mcp-gateway:8820").rstrip("/")
AUTH_TOKEN = os.getenv("MCP_GATEWAY_AUTH_TOKEN", "").strip()
WORKSPACE_TARGET = os.getenv("MCP_WORKSPACE_TARGET_PATH", "/workspace").rstrip("/")
WORKSPACE_SOURCE = os.getenv(
    "MCP_WORKSPACE_SOURCE_PATH",
    "/run/desktop/mnt/host/h/HYPERFOCUSZONE/HperCore/HyperCode-V2.4",
).rstrip("/")
LOCAL_WORKSPACE_ROOT = os.getenv("MCP_LOCAL_WORKSPACE_ROOT", "/workspace").rstrip("/")

# Latest protocol version we advertise; the gateway negotiates down if needed.
CLIENT_PROTOCOL_VERSION = "2025-06-18"


def _derive_mcp_endpoint() -> str:
    """Resolve the Streamable HTTP endpoint.

    Prefers MCP_GATEWAY_MCP_URL; otherwise rewrites a legacy `/sse` URL to
    `/mcp`, or falls back to `<base>/mcp`.
    """
    explicit = os.getenv("MCP_GATEWAY_MCP_URL", "").strip().rstrip("/")
    if explicit:
        return explicit
    legacy = os.getenv("MCP_GATEWAY_SSE_URL", "").strip().rstrip("/")
    if legacy.endswith("/sse"):
        return legacy[:-4] + "/mcp"
    if legacy:
        return legacy
    return f"{GATEWAY_BASE}/mcp"


MCP_ENDPOINT = _derive_mcp_endpoint()

app = FastAPI()


async def require_mcp_token(authorization: str | None = Header(default=None)) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization: Bearer <token> required")
    token = authorization.removeprefix("Bearer ").strip()
    expected = os.environ.get("MCP_REST_ADAPTER_AUTH_TOKEN", "").strip()
    if not expected or not hmac.compare_digest(token.encode("utf-8"), expected.encode("utf-8")):
        raise HTTPException(status_code=403, detail="Invalid token")


class ToolCallRequest(BaseModel):
    tool: str
    params: Dict[str, Any] = {}
    action: Optional[str] = None


def _base_headers() -> Dict[str, str]:
    """Headers for the initial (pre-session) POST."""
    headers = {
        "Content-Type": "application/json",
        # Streamable HTTP requires the client to accept both shapes.
        "Accept": "application/json, text/event-stream",
    }
    if AUTH_TOKEN:
        headers["Authorization"] = f"Bearer {AUTH_TOKEN}"
    return headers


def _extract_jsonrpc_message(resp: httpx.Response, expect_id: Optional[str]) -> Any:
    """Pull a JSON-RPC message out of a Streamable HTTP response.

    Handles both `application/json` (one message) and `text/event-stream`
    (one or more SSE `data:` events). When `expect_id` is given, returns the
    message whose `id` matches; otherwise returns the first dict message.
    """
    content_type = resp.headers.get("content-type", "")

    if "text/event-stream" not in content_type:
        try:
            return resp.json()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=502,
                detail=f"Invalid JSON from MCP gateway: {resp.text[:200]}",
            ) from exc

    # SSE: events are `data:` lines terminated by a blank line.
    data_lines: list[str] = []
    fallback: Optional[Dict[str, Any]] = None

    def _consume(lines: list[str]) -> Optional[Any]:
        nonlocal fallback
        if not lines:
            return None
        payload = "\n".join(lines).strip()
        if not payload:
            return None
        try:
            msg = json.loads(payload)
        except Exception:  # noqa: BLE001
            return None
        if not isinstance(msg, dict):
            return None
        if expect_id is None or str(msg.get("id", "")) == str(expect_id):
            return msg
        # Remember a result/error message in case no id ever matches.
        if fallback is None and ("result" in msg or "error" in msg):
            fallback = msg
        return None

    for raw in resp.text.splitlines():
        line = raw.rstrip("\r")
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
        elif line == "":
            found = _consume(data_lines)
            data_lines = []
            if found is not None:
                return found
    found = _consume(data_lines)  # trailing event with no closing blank line
    if found is not None:
        return found
    if fallback is not None:
        return fallback
    raise HTTPException(
        status_code=502, detail="No JSON-RPC message in MCP gateway response"
    )


async def _jsonrpc(method: str, params: Dict[str, Any]) -> Any:
    """Run one MCP method over a fresh Streamable HTTP session."""
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        # 1. initialize -------------------------------------------------------
        init_id = str(uuid.uuid4())
        init_resp = await client.post(
            MCP_ENDPOINT,
            headers=_base_headers(),
            json={
                "jsonrpc": "2.0",
                "id": init_id,
                "method": "initialize",
                "params": {
                    "protocolVersion": CLIENT_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "mcp-rest-adapter", "version": "0.2"},
                },
            },
        )
        if init_resp.status_code >= 400:
            raise HTTPException(
                status_code=502,
                detail=f"MCP initialize failed: {init_resp.status_code} "
                f"{init_resp.text[:200]}",
            )

        session_id = init_resp.headers.get("mcp-session-id")
        init_msg = _extract_jsonrpc_message(init_resp, init_id)
        if isinstance(init_msg, dict) and init_msg.get("error"):
            raise HTTPException(status_code=502, detail=init_msg["error"])

        negotiated = CLIENT_PROTOCOL_VERSION
        if isinstance(init_msg, dict):
            result = init_msg.get("result")
            if isinstance(result, dict) and result.get("protocolVersion"):
                negotiated = str(result["protocolVersion"])

        session_headers = _base_headers()
        session_headers["MCP-Protocol-Version"] = negotiated
        if session_id:
            session_headers["Mcp-Session-Id"] = session_id

        try:
            # 2. notifications/initialized (no id — fire and forget) ----------
            try:
                await client.post(
                    MCP_ENDPOINT,
                    headers=session_headers,
                    json={
                        "jsonrpc": "2.0",
                        "method": "notifications/initialized",
                        "params": {},
                    },
                )
            except Exception:  # noqa: BLE001 — best effort
                pass

            # 3. the real call ------------------------------------------------
            req_id = str(uuid.uuid4())
            resp = await client.post(
                MCP_ENDPOINT,
                headers=session_headers,
                json={
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "method": method,
                    "params": params,
                },
            )
            if resp.status_code >= 400:
                raise HTTPException(
                    status_code=502,
                    detail=f"MCP {method} failed: {resp.status_code} "
                    f"{resp.text[:200]}",
                )
            msg = _extract_jsonrpc_message(resp, req_id)
            if isinstance(msg, dict) and msg.get("error"):
                raise HTTPException(status_code=502, detail=msg["error"])
            if isinstance(msg, dict):
                return msg.get("result")
            return msg
        finally:
            # 4. terminate the session (best effort) --------------------------
            if session_id:
                try:
                    await client.delete(MCP_ENDPOINT, headers=session_headers)
                except Exception:  # noqa: BLE001
                    pass


def _normalize_tool_call(body: ToolCallRequest) -> Dict[str, Any]:
    if ":" in body.tool:
        return {"tool": body.tool, "params": body.params}

    tool = body.tool.strip().lower()
    action = (body.action or "").strip().lower()

    if tool == "filesystem" and action in {"list", "list_directory"}:
        return {"tool": "filesystem:list_directory", "params": {"path": body.params.get("path", "/")}}

    if tool == "github" and action == "list_repos":
        owner = body.params.get("owner", "")
        if not isinstance(owner, str) or not owner:
            raise HTTPException(status_code=400, detail="Missing github owner")
        return {"tool": "search_repositories", "params": {"query": f"org:{owner}"}}

    if tool == "postgres" and action:
        return {"tool": f"{tool}:{action}", "params": body.params}

    raise HTTPException(status_code=400, detail="Unsupported tool/action format")


@app.get("/health")
async def health():
    return {"status": "ok", "transport": "streamable-http", "endpoint": MCP_ENDPOINT}


@app.get("/tools/discover", dependencies=[Depends(require_mcp_token)])
async def tools_discover():
    tools = await _jsonrpc("tools/list", {})
    tool_list = None
    if isinstance(tools, dict) and isinstance(tools.get("tools"), list):
        tool_list = tools["tools"]
    elif isinstance(tools, list):
        tool_list = tools

    if tool_list is not None:
        if not any(isinstance(t, dict) and t.get("name") == "filesystem:list_directory" for t in tool_list):
            tool_list.append(
                {
                    "name": "filesystem:list_directory",
                    "description": "List a directory path (adapter-local fallback).",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"],
                    },
                }
            )
        if not any(isinstance(t, dict) and t.get("name") == "github:list_repos" for t in tool_list):
            tool_list.append(
                {
                    "name": "github:list_repos",
                    "description": "List repos for a GitHub org/user (adapter-local fallback).",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"owner": {"type": "string"}},
                        "required": ["owner"],
                    },
                }
            )
    return tools


# The MCP gateway exposes no `filesystem` server, so directory listing AND
# file reads are served locally from the read-only `/workspace` bind mount.
MAX_READ_BYTES = 1_000_000


def _is_workspace_path(path: str) -> bool:
    return path == WORKSPACE_TARGET or path.startswith(WORKSPACE_TARGET + "/")


def _resolve_in_workspace(path: str) -> Path:
    """Translate a `/workspace/...` path to a real path, sandboxed to the root."""
    root = Path(LOCAL_WORKSPACE_ROOT)
    p = Path(path)
    if str(p) == WORKSPACE_TARGET:
        p = root
    elif str(p).startswith(WORKSPACE_TARGET + "/"):
        p = root / str(p)[len(WORKSPACE_TARGET) + 1 :]

    try:
        resolved = p.resolve()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path")

    try:
        resolved.relative_to(root.resolve())
    except Exception:
        raise HTTPException(status_code=403, detail="Path outside workspace")

    return resolved


def _local_list_directory(path: str) -> Dict[str, Any]:
    resolved = _resolve_in_workspace(path)
    if not resolved.exists() or not resolved.is_dir():
        raise HTTPException(status_code=404, detail="Directory not found")

    entries = []
    for child in sorted(resolved.iterdir(), key=lambda x: x.name.lower()):
        entries.append(
            {
                "name": child.name,
                "path": f"{WORKSPACE_TARGET}/{child.name}".replace("//", "/"),
                "type": "directory" if child.is_dir() else "file",
            }
        )
    return {"path": str(path), "entries": entries}


def _local_read_file(path: str) -> Dict[str, Any]:
    resolved = _resolve_in_workspace(path)
    if not resolved.exists() or not resolved.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    size = resolved.stat().st_size
    if size > MAX_READ_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size} bytes, cap {MAX_READ_BYTES})",
        )
    try:
        content = resolved.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=415, detail="Binary file — not displayable as text")
    return {"path": str(path), "content": content}


@app.post("/tools/call", dependencies=[Depends(require_mcp_token)])
async def tools_call(body: ToolCallRequest):
    normalized = _normalize_tool_call(body)
    tool = normalized["tool"]
    params = normalized["params"]

    if tool in {"filesystem:list_directory", "filesystem"}:
        p = params.get("path", "/")
        if isinstance(p, str) and _is_workspace_path(p):
            return {"result": _local_list_directory(p)}

    if tool in {"filesystem:read_file", "filesystem:read_text_file"}:
        p = params.get("path", "")
        if isinstance(p, str) and _is_workspace_path(p):
            return {"result": _local_read_file(p)}

    result = await _jsonrpc("tools/call", {"name": tool, "arguments": params})
    return {"result": result}
