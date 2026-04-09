"""
base_agent.py

Shared agent runtime for HyperCode specialist agents.

Key requirements:
- Exposes FastAPI POST /execute (crew-orchestrator compatible)
- Uses Anthropic when configured, otherwise returns a safe fallback
- Avoids direct `project_memory.redis` usage (project memory is an in-memory KV stub here)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict

try:
    import redis.asyncio as aioredis  # type: ignore
except Exception:  # pragma: no cover
    aioredis = None

try:
    import anthropic  # type: ignore
except Exception:  # pragma: no cover
    anthropic = None

try:
    import structlog  # type: ignore
except Exception:  # pragma: no cover
    structlog = None


class _StdLoggerAdapter:
    def __init__(self, name: str) -> None:
        import logging

        logging.basicConfig(level=logging.INFO)
        self._logger = logging.getLogger(name)

    def info(self, event: str, **kwargs: Any) -> None:
        self._logger.info("%s %s", event, kwargs if kwargs else "")

    def warning(self, event: str, **kwargs: Any) -> None:
        self._logger.warning("%s %s", event, kwargs if kwargs else "")

    def error(self, event: str, **kwargs: Any) -> None:
        self._logger.error("%s %s", event, kwargs if kwargs else "")

    def exception(self, event: str, **kwargs: Any) -> None:
        self._logger.exception("%s %s", event, kwargs if kwargs else "")


@dataclass
class AgentConfig:
    name: str = os.getenv("AGENT_NAME", "base-agent")
    role: str = os.getenv("AGENT_ROLE", "Generic Agent")
    port: int = int(os.getenv("AGENT_PORT", "8000"))
    model: str = os.getenv("AGENT_MODEL", "claude-3-5-sonnet-20241022")
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    extra: dict = field(default_factory=dict)


class TaskRequest(BaseModel):
    """
    Crew-orchestrator sends:
      {"id": "...", "task": "...", "type": "...", "requires_approval": false, "context": {...}}
    Support legacy variants too (task_id/description) and allow extra fields.
    """

    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    task_id: Optional[str] = None
    task: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = "generic"
    context: Optional[Dict[str, Any]] = None
    requires_approval: bool = False


class AgentMemory:
    """Minimal RAG stub; keep synchronous for existing agent implementations."""

    def query_relevant_context(self, query: str) -> str:
        return ""


class ProjectMemory:
    """
    Minimal project memory KV used by tests/agents.
    Intentionally does NOT expose `.redis` to prevent broken call sites.
    """

    def __init__(self) -> None:
        self._data: Dict[str, Any] = {"available_apis": []}

    def get_project_context(self) -> Dict[str, Any]:
        return dict(self._data)

    def set_value(self, key: str, value: Any) -> None:
        self._data[key] = value

    def add_api_endpoint(self, endpoint: str) -> None:
        apis = self._data.setdefault("available_apis", [])
        if isinstance(apis, list) and endpoint not in apis:
            apis.append(endpoint)


class ApprovalSystem:
    """Auto-approves tasks in dev/test mode."""

    async def request_approval(
        self, agent_name: str, action: str, payload: Dict[str, Any], timeout: int = 300
    ) -> Dict[str, Any]:
        _ = (agent_name, action, payload, timeout)
        return {"status": "approved"}


class BaseAgent:
    def __init__(self, config: Optional[AgentConfig] = None) -> None:
        self.config = config or AgentConfig()
        self.logger = (
            structlog.get_logger(self.config.name) if structlog else _StdLoggerAdapter(self.config.name)
        )

        # Shared systems
        self.redis = None
        self.agent_memory = AgentMemory()
        self.project_memory = ProjectMemory()
        self.approval_system = ApprovalSystem()
        self.tools: list[Callable[..., Any]] = []

        # LLM client (Anthropic)
        self.client = None
        if anthropic and self.config.anthropic_api_key:
            self.client = anthropic.AsyncAnthropic(api_key=self.config.anthropic_api_key)

        self.app = FastAPI(title=f"{self.config.name} Agent")
        self._setup_routes()

    # ---------- lifecycle ----------
    async def startup(self) -> None:
        await self._connect_redis()
        await self.initialize()

    async def shutdown(self) -> None:
        if self.redis:
            try:
                await self.redis.set(f"agent:{self.config.name}:status", "offline")
                await self.redis.aclose()
            except Exception:
                pass

    async def initialize(self) -> None:
        """Hook for subclasses (e.g., background tasks)."""

    def register_tool(self, tool_func: Callable[..., Any]) -> None:
        self.tools.append(tool_func)

    async def _connect_redis(self) -> None:
        if not aioredis:
            return
        try:
            self.redis = await aioredis.from_url(
                self.config.redis_url, encoding="utf-8", decode_responses=True
            )
            await self.redis.set(f"agent:{self.config.name}:status", "online")
        except Exception as exc:
            self.redis = None
            self.logger.warning("redis_unavailable", error=str(exc))

    # ---------- LLM ----------
    def build_system_prompt(self) -> str:
        return f"""You are {self.config.name} ({self.config.role}) in the HyperCode agent swarm.

Return concise, actionable output. Prefer bullet points, short steps, and code blocks when helpful.
"""

    async def _llm_text(self, *, system: str, user: str, max_tokens: int = 2000) -> str:
        if not self.client:
            return "No LLM client configured (set ANTHROPIC_API_KEY). Returning fallback response."

        try:
            resp = await self.client.messages.create(
                model=self.config.model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            return resp.content[0].text
        except Exception as exc:
            self.logger.error("llm_call_failed", error=str(exc))
            return f"LLM call failed: {exc}"

    # ---------- execution ----------
    async def process_task(self, task: str, context: Dict[str, Any], requires_approval: bool = False) -> Any:
        """
        Default behavior: return LLM output for the task.
        Subclasses can override and still call `_llm_text(...)`.
        """
        rag_context = self.agent_memory.query_relevant_context(task) if self.agent_memory else ""
        project_context = self.project_memory.get_project_context() if self.project_memory else {}

        system = self.build_system_prompt()
        user = f"""TASK:
{task}

CONTEXT:
{context or {}}

RAG CONTEXT:
{rag_context}

PROJECT CONTEXT:
{project_context}
"""
        if requires_approval and self.approval_system:
            approval = await self.approval_system.request_approval(
                self.config.name, "execute_task", {"task": task}, timeout=300
            )
            if approval.get("status") != "approved":
                raise RuntimeError(f"Task rejected: {approval.get('reason')}")

        return await self._llm_text(system=system, user=user)

    # ---------- FastAPI ----------
    def _setup_routes(self) -> None:
        @self.app.on_event("startup")
        async def _startup() -> None:
            await self.startup()

        @self.app.on_event("shutdown")
        async def _shutdown() -> None:
            await self.shutdown()

        @self.app.get("/health")
        async def health() -> Dict[str, Any]:
            return {"status": "healthy", "agent": self.config.name}

        @self.app.post("/execute")
        async def execute(req: TaskRequest) -> Dict[str, Any]:
            task_text = (req.description or req.task or "").strip()
            if not task_text:
                raise HTTPException(status_code=422, detail="Missing task/description")

            task_id = req.id or req.task_id or "unknown"
            try:
                result = await self.process_task(task_text, req.context or {}, req.requires_approval)
                return {"status": "success", "task_id": task_id, "agent": self.config.name, "result": result}
            except HTTPException:
                raise
            except Exception as exc:
                self.logger.exception("task_failed", error=str(exc), task_id=task_id)
                raise HTTPException(status_code=500, detail=str(exc))

        # Backwards compatibility for older callers
        @self.app.post("/task")
        async def task_alias(payload: Dict[str, Any]) -> Dict[str, Any]:
            req = TaskRequest(**payload)
            return await execute(req)

    def run(self) -> None:
        import uvicorn

        uvicorn.run(self.app, host="0.0.0.0", port=self.config.port)

