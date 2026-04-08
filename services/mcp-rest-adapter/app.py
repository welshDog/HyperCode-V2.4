import json
import os
import time
import uuid
from typing import Any, Dict, Optional
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

GATEWAY_BASE = os.getenv("MCP_GATEWAY_BASE_URL", "http://mcp-gateway:8820").rstrip("/")
SSE_BOOT_URL = os.getenv("MCP_GATEWAY_SSE_URL", f"{GATEWAY_BASE}/sse")
AUTH_TOKEN = os.getenv("MCP_GATEWAY_AUTH_TOKEN", "").strip()
WORKSPACE_TARGET = os.getenv("MCP_WORKSPACE_TARGET_PATH", "/workspace").rstrip("/")
WORKSPACE_SOURCE = os.getenv(
    "MCP_WORKSPACE_SOURCE_PATH",
    "/run/desktop/mnt/host/h/HyperStation zone/HyperCode/HyperCode-V2.4",
).rstrip("/")
LOCAL_WORKSPACE_ROOT = os.getenv("MCP_LOCAL_WORKSPACE_ROOT", "/workspace").rstrip("/")

app = FastAPI()


class ToolCallRequest(BaseModel):
    tool: str
    params: Dict[str, Any] = {}
    action: Optional[str] = None


def _headers() -> Dict[str, str]:
    if not AUTH_TOKEN:
        return {}
    return {"Authorization": f"Bearer {AUTH_TOKEN}"}


async def _await_jsonrpc_response(
    stream: httpx.Response, req_id: str, timeout_s: float = 20.0
) -> Dict[str, Any]:
    start = time.time()
    data_lines: list[str] = []
    async for line in stream.aiter_lines():
        if time.time() - start > timeout_s:
            raise TimeoutError("Timed out waiting for MCP response")
        if line.startswith("data:"):
            data_lines.append(line.split(":", 1)[1].strip())
        elif line == "":
            if not data_lines:
                continue
            payload = "\n".join(data_lines).strip()
            data_lines = []
            try:
                msg = json.loads(payload)
            except Exception:
                continue
            if isinstance(msg, dict) and str(msg.get("id", "")) == str(req_id):
                return msg
    raise TimeoutError("Stream ended before MCP response arrived")


async def _jsonrpc(method: str, params: Dict[str, Any]) -> Any:
    async with httpx.AsyncClient(timeout=30) as client:
        async with client.stream("GET", SSE_BOOT_URL, headers=_headers()) as stream:
            stream.raise_for_status()
            post_url = None
            init_id = None
            req_id = None
            stage = "endpoint"
            event = None
            data_lines: list[str] = []
            start = time.time()

            async for line in stream.aiter_lines():
                if time.time() - start > 25:
                    raise HTTPException(status_code=504, detail="MCP gateway response timeout")

                if line.startswith("event:"):
                    event = line.split(":", 1)[1].strip()
                    continue

                if line.startswith("data:"):
                    data_lines.append(line.split(":", 1)[1].strip())
                    continue

                if line != "":
                    continue

                if not data_lines:
                    continue

                payload = "\n".join(data_lines).strip()
                data_lines = []
                if stage == "endpoint" and event == "endpoint":
                    post_url = payload if payload.startswith("http") else f"{GATEWAY_BASE}{payload}"
                    init_id = str(uuid.uuid4())
                    await client.post(
                        post_url,
                        headers={**_headers(), "Content-Type": "application/json"},
                        json={
                            "jsonrpc": "2.0",
                            "id": init_id,
                            "method": "initialize",
                            "params": {
                                "protocolVersion": "2024-11-05",
                                "capabilities": {},
                                "clientInfo": {"name": "mcp-rest-adapter", "version": "0.1"},
                            },
                        },
                    )
                    stage = "init"
                    event = None
                    continue

                try:
                    msg = json.loads(payload)
                except Exception:
                    event = None
                    continue

                if not isinstance(msg, dict):
                    event = None
                    continue

                mid = str(msg.get("id", ""))

                if stage == "init" and init_id is not None and mid == init_id:
                    if msg.get("error"):
                        raise HTTPException(status_code=502, detail=msg["error"])

                    await client.post(
                        post_url,
                        headers={**_headers(), "Content-Type": "application/json"},
                        json={"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}},
                    )

                    req_id = str(uuid.uuid4())
                    await client.post(
                        post_url,
                        headers={**_headers(), "Content-Type": "application/json"},
                        json={"jsonrpc": "2.0", "id": req_id, "method": method, "params": params},
                    )
                    stage = "req"
                    event = None
                    continue

                if stage == "req" and req_id is not None and mid == req_id:
                    if msg.get("error"):
                        raise HTTPException(status_code=502, detail=msg["error"])
                    return msg.get("result")

                event = None

            raise HTTPException(status_code=502, detail="MCP gateway stream ended unexpectedly")


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
    return {"status": "ok"}


@app.get("/tools/discover")
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


def _local_list_directory(path: str) -> Dict[str, Any]:
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


@app.post("/tools/call")
async def tools_call(body: ToolCallRequest):
    normalized = _normalize_tool_call(body)
    if normalized["tool"] in {"filesystem:list_directory", "filesystem"}:
        p = normalized["params"].get("path", "/")
        if isinstance(p, str) and (p == WORKSPACE_TARGET or p.startswith(WORKSPACE_TARGET + "/")):
            return {"result": _local_list_directory(p)}
    result = await _jsonrpc(
        "tools/call", {"name": normalized["tool"], "arguments": normalized["params"]}
    )
    return {"result": result}
