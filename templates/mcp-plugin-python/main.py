from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="ND Safe MCP Plugin", version="0.1.0")


class Tool(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]


class ToolsResponse(BaseModel):
    tools: list[Tool]


class ExecuteRequest(BaseModel):
    tool_name: str
    params: dict[str, Any] = {}


_MANIFEST = json.loads(Path(__file__).with_name("manifest.json").read_text(encoding="utf-8"))


@app.get("/mcp/tools", response_model=ToolsResponse)
async def list_tools() -> ToolsResponse:
    tools = [Tool(**t) for t in _MANIFEST.get("tools", [])]
    return ToolsResponse(tools=tools)


@app.post("/mcp/execute")
async def execute_tool(req: ExecuteRequest) -> dict[str, Any]:
    if req.tool_name == "focus.start":
        minutes = int(req.params.get("minutes", 25))
        mode = str(req.params.get("mode", "focus"))
        return {
            "ok": True,
            "result": {
                "minutes": minutes,
                "mode": mode,
                "message": "Focus session started",
            },
        }
    return {"ok": False, "error": "Unknown tool"}

