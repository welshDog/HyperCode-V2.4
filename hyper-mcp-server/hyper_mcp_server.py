from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Hyper MCP Server", version="2.0.0")

# ── Internal Agent URLs (from .env — NEVER hardcoded) ──────
BROSKI_AGENT_URL = os.getenv("BROSKI_AGENT_URL", "http://localhost:8001")
BRAIN_CORE_URL   = os.getenv("BRAIN_CORE_URL",   "http://localhost:8002")
SKILLS_API_URL   = os.getenv("SKILLS_API_URL",   "http://localhost:8003")

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
            "required": ["task"]
        }
    },
    {
        "name": "brain_core_agent",
        "description": "Hyper Brain Core — memory, context, second brain queries.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to look up"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "hyper_skill_agent",
        "description": "Load and execute a HYPER-SILLs skill by ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "skill_id": {"type": "string", "description": "e.g. HS-081"}
            },
            "required": ["skill_id"]
        }
    }
]

# ── Skills-Over-MCP Resources (SEP-2640) ───────────────────
SKILLS_INDEX = [
    {"uri": "skill://HS-081", "id": "HS-081", "hero_name": "PORTAL FORGE", "category": "dev", "description": "MCP Server + Agent Registration Pattern"},
    {"uri": "skill://HS-129", "id": "HS-129", "hero_name": "SKILLS-OVER-MCP", "category": "dev", "description": "Expose Skills as MCP Resources (SEP-2640)"},
    {"uri": "skill://HS-018", "id": "HS-018", "hero_name": "BRIDGE KEEPER", "category": "agents", "description": "MCP Bridge Manifest"},
    {"uri": "skill://HS-017", "id": "HS-017", "hero_name": "MIND CORE", "category": "agents", "description": "Hyper Brain Core Manifest"},
]

# ── MCP Tool Endpoints ─────────────────────────────────────

@app.get("/tools/list")
async def tools_list():
    return {"tools": TOOLS}


class ToolCallRequest(BaseModel):
    name: str
    arguments: dict[str, Any]


@app.post("/tools/call")
async def tools_call(req: ToolCallRequest):
    async with httpx.AsyncClient(timeout=15.0) as client:

        if req.name == "broski_agent":
            resp = await client.post(
                f"{BROSKI_AGENT_URL}/run",
                json={"task": req.arguments.get("task")}
            )
            result = resp.json().get("result", "No response from BROski agent")

        elif req.name == "brain_core_agent":
            resp = await client.post(
                f"{BRAIN_CORE_URL}/query",
                json={"query": req.arguments.get("query")}
            )
            result = resp.json().get("answer", "No response from Brain Core")

        elif req.name == "hyper_skill_agent":
            resp = await client.get(
                f"{SKILLS_API_URL}/skill/{req.arguments.get('skill_id')}"
            )
            result = resp.json().get("content", "Skill not found")

        else:
            return {"error": f"Unknown tool: {req.name}"}

    return {
        "content": [{"type": "text", "text": result}]
    }


# ── Skills-Over-MCP Resource Endpoints (SEP-2640) ──────────

@app.get("/resources/list")
async def resources_list():
    """SEP-2640 skills://index — browse all skills"""
    return {"resources": SKILLS_INDEX}


@app.get("/resources/read")
async def resources_read(uri: str):
    """SEP-2640 skill://HS-NNN — read one skill"""
    skill_id = uri.replace("skill://", "")
    match = next((s for s in SKILLS_INDEX if s["id"] == skill_id), None)
    if not match:
        return {
            "content": [{"type": "text", "text": f"⚠️ Skill {skill_id} not found. Try skills://index to browse available skills."}]
        }
    return {
        "content": [{"type": "text", "text": f"Skill: {match['hero_name']}\nCategory: {match['category']}\nDescription: {match['description']}"}]
    }


# ── Health ─────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "online", "server": "Hyper MCP v2", "sep_2640": "tracking"}
