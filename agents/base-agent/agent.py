"""
Base Agent Template for HyperCode Crew
Each specialized agent extends this base
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import asyncio
import os
import secrets
import redis.asyncio as redis
from contextlib import asynccontextmanager
import sys

# Allow imports from shared modules
sys.path.insert(0, "/app")
try:
    from shared.rag_memory import AgentMemory
    from shared.project_memory import ProjectMemory
    from shared.logging_config import setup_logging
    from shared.approval_system import ApprovalSystem
except ImportError:
    print("\u26a0\ufe0f Shared modules not found, running in limited mode")
    AgentMemory = None
    ProjectMemory = None
    def setup_logging(agent_name: str):
        return None
    ApprovalSystem = None

# HyperAlert - safe import guard (no crash if module not yet mounted)
try:
    from shared.discord_alerts import HyperAlert
except ImportError:
    HyperAlert = None

# AI Client \u2014 try anthropic first, fallback to openai
try:
    from anthropic import AsyncAnthropic as AIClient
    ai_backend = "anthropic"
except ImportError:
    try:
        from openai import AsyncOpenAI as AIClient
        ai_backend = "openai"
    except ImportError:
        AIClient = None
        ai_backend = None
        print("\u26a0\ufe0f No AI client found (anthropic or openai). Running in limited mode.")

def _resolve_secret(var: str) -> Optional[str]:
    """Return env ``var``, or the content of ``<var>_FILE`` if set (Docker secrets)."""
    file_path = os.getenv(f"{var}_FILE")
    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as fh:
                return fh.read().strip()
        except OSError:
            pass
    return os.getenv(var)


class AgentConfig:
    """Base configuration for all agents"""
    def __init__(self):
        self.name = os.getenv("AGENT_NAME", "base-agent")
        self.role = os.getenv("AGENT_ROLE", "Generic Agent")
        self.model = os.getenv("AGENT_MODEL", "claude-3-5-sonnet-20241022")
        self.port = int(os.getenv("AGENT_PORT", "8001"))
        self.api_key = (
            _resolve_secret("ANTHROPIC_API_KEY")
            or _resolve_secret("PERPLEXITY_API_KEY")
            or _resolve_secret("OPENAI_API_KEY")
        )
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
        self.core_url = os.getenv("CORE_URL", "http://hypercode-core:8000")
        self.hypercode_api_key = _resolve_secret("HYPERCODE_API_KEY")

class TaskRequest(BaseModel):
    id: Optional[str] = None
    task_id: Optional[str] = None
    task: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = "generic"
    context: Optional[Dict[str, Any]] = None
    requires_approval: bool = True

class TaskResponse(BaseModel):
    task_id: Optional[str] = None
    agent: Optional[str] = None
    status: str
    result: Any
    error: Optional[str] = None

class BaseAgent:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.logger = setup_logging(config.name)
        
        self.redis = None
        self.agent_memory = None
        self.project_memory = None
        self.approval_system = None
        self.client = None

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            """Initialize shared systems on startup"""
            await self.startup()
            yield
            await self.shutdown()

        self.app = FastAPI(title=f"{config.name} Agent", lifespan=lifespan)
        @self.app.middleware("http")
        async def _agent_auth_middleware(request: Request, call_next):
            path = request.url.path
            if path == "/" or path.startswith("/health"):
                return await call_next(request)

            expected = (self.config.hypercode_api_key or os.getenv("AGENT_API_KEY") or "").strip()
            if not expected:
                return JSONResponse(status_code=503, content={"detail": "Agent API key not configured"})

            provided = request.headers.get("x-agent-key") or request.headers.get("x-api-key")
            if not provided or not secrets.compare_digest(str(provided), expected):
                return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})

            return await call_next(request)
        self.setup_routes()

    async def startup(self):
        if self.logger:
            self.logger.info("initializing_agent", agent=self.config.name)

        # Initialize Redis with retry
        for attempt in range(5):
            try:
                self.redis = await redis.from_url(self.config.redis_url, decode_responses=True)
                await self.redis.ping()
                if self.logger:
                    self.logger.info("redis_connected")
                break
            except Exception as e:
                wait = 2 ** attempt
                if self.logger:
                    self.logger.warning(f"Redis connect failed (attempt {attempt + 1}): {e}. Retry in {wait}s")
                await asyncio.sleep(wait)
        else:
            raise RuntimeError("Could not connect to Redis after 5 attempts")
        
        # Initialize AI Client
        if AIClient and self.config.api_key:
            self.client = AIClient(api_key=self.config.api_key)
        
        # Initialize Shared Systems
        try:
            if AgentMemory:
                self.agent_memory = AgentMemory(self.config.name)
                bible_path = "/app/HYPER-AGENT-BIBLE.md"
                if os.path.exists(bible_path):
                    self.agent_memory.ingest_document(bible_path)
            
            if ProjectMemory:
                self.project_memory = ProjectMemory(self.config.redis_url)
        except Exception:
            if self.logger:
                self.logger.warning("Shared memory modules not available")
            
        await self.initialize()

        # \U0001f4e2 Fleet heartbeat: fire agent_started Discord alert on every boot
        if HyperAlert:
            try:
                await HyperAlert.agent_started(self.config.name)
            except Exception as _alert_err:
                if self.logger:
                    self.logger.warning(f"HyperAlert.agent_started failed (non-fatal): {_alert_err}")

    async def initialize(self):
        """Hook for subclasses to add custom initialization logic"""
        pass

    def register_tool(self, tool_func):
        if self.logger:
            self.logger.info(f"Registered tool: {tool_func.__name__}")
            
        if ApprovalSystem:
            self.approval_system = ApprovalSystem(self.config.redis_url)

        if self.logger:
            self.logger.info("agent_ready")

    async def shutdown(self):
        if self.redis:
            await self.redis.close()
        if self.logger:
            self.logger.info("agent_shutdown")

    def setup_routes(self):
        @self.app.get("/")
        async def root():
            return {
                "agent": self.config.name,
                "role": self.config.role,
                "status": "ready"
            }
        
        @self.app.get("/health")
        async def health():
            try:
                if self.redis:
                    await self.redis.ping()
                return {"status": "healthy"}
            except Exception:
                raise HTTPException(status_code=503, detail="Redis unavailable")
        
        @self.app.post("/task")
        async def execute_task(request: TaskRequest) -> TaskResponse:
            task_id = request.task_id or request.id or secrets.token_hex(8)
            try:
                task_text = request.task or request.description or ""
                result = await self.process_task(task_text, request.context or {})
                return TaskResponse(
                    task_id=task_id,
                    agent=self.config.name,
                    status="completed",
                    result=result
                )
            except Exception as e:
                if self.logger:
                    self.logger.error("task_failed", task_id=task_id, error=str(e))
                return TaskResponse(
                    task_id=task_id,
                    agent=self.config.name,
                    status="error",
                    result=None,
                    error=str(e)
                )

    async def process_task(self, task: str, context: Dict[str, Any]) -> Any:
        """Override in subclasses to implement agent-specific logic"""
        return {"message": f"Task received by {self.config.name}: {task}"}
