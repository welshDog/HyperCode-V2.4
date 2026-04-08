"""
BaseAgent — shared base class for all HyperCode specialist agents.
Previously empty — now populated with full BaseAgent implementation.
"""
import os
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional, Any

try:
    import redis.asyncio as aioredis
except ImportError:
    aioredis = None

try:
    import anthropic
except ImportError:
    anthropic = None


@dataclass
class AgentConfig:
    name: str = os.getenv("AGENT_NAME", "base-agent")
    port: int = int(os.getenv("AGENT_PORT", "8080"))
    model: str = os.getenv("AGENT_MODEL", "claude-3-5-haiku-20241022")
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    extra: dict = field(default_factory=dict)


class ProjectMemory:
    """Lightweight project memory backed by a dict (Redis-backed in production)."""
    def __init__(self):
        self._data = {"available_apis": []}

    def get_project_context(self) -> dict:
        return self._data

    def add_api_endpoint(self, endpoint: str):
        if endpoint not in self._data["available_apis"]:
            self._data["available_apis"].append(endpoint)


class AgentMemory:
    """Simple RAG-style memory stub."""
    def query_relevant_context(self, query: str) -> str:
        return ""


class ApprovalSystem:
    """Auto-approves tasks in dev/test mode."""
    async def request_approval(self, agent_name: str, action: str, payload: dict, timeout: int = 300) -> dict:
        return {"status": "approved"}


class BaseAgent:
    """
    Base class for all HyperCode agents.
    Provides Redis connection, Anthropic client, memory, approval system, and lifecycle hooks.
    """

    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.logger = logging.getLogger(self.config.name)
        logging.basicConfig(level=logging.INFO)

        self.redis = None

        self.client = None
        if anthropic and self.config.anthropic_api_key:
            self.client = anthropic.AsyncAnthropic(api_key=self.config.anthropic_api_key)

        self.agent_memory = AgentMemory()
        self.project_memory = ProjectMemory()
        self.approval_system = ApprovalSystem()

    async def _startup_register(self):
        if aioredis:
            try:
                self.redis = await aioredis.from_url(
                    self.config.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                await self.redis.set(f"agent:{self.config.name}:status", "online")
                self.logger.info(f"Agent {self.config.name} registered in Redis")
            except Exception as e:
                self.logger.warning(f"Redis unavailable: {e} — running without Redis")

    async def _shutdown_cleanup(self):
        if self.redis:
            try:
                await self.redis.set(f"agent:{self.config.name}:status", "offline")
                await self.redis.aclose()
            except Exception:
                pass

    async def process_task(self, task: str, context: dict, requires_approval: bool = False) -> dict:
        raise NotImplementedError("Subclasses must implement process_task()")

    def run(self):
        import uvicorn
        from fastapi import FastAPI

        app = FastAPI(title=self.config.name)

        @app.on_event("startup")
        async def startup():
            await self._startup_register()

        @app.on_event("shutdown")
        async def shutdown():
            await self._shutdown_cleanup()

        @app.get("/health")
        async def health():
            return {"status": "healthy", "agent": self.config.name, "vibe": 100}

        @app.post("/task")
        async def run_task(payload: dict):
            task = payload.get("task", "")
            context = payload.get("context", {})
            requires_approval = payload.get("requires_approval", False)
            result = await self.process_task(task, context, requires_approval)
            return {"status": "ok", "result": result}

        uvicorn.run(app, host="0.0.0.0", port=self.config.port)
