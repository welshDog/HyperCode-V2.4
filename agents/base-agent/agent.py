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
    print("⚠️ Shared modules not found, running in limited mode")
    AgentMemory = None
    ProjectMemory = None
    def setup_logging(agent_name: str):
        return None
    ApprovalSystem = None

# AI Client — try anthropic first, fallback to openai
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
        print("⚠️ No AI client found (anthropic or openai). Running in limited mode.")

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
            except Exception as e:
                raise HTTPException(status_code=503, detail=str(e))

        @self.app.post("/execute")
        async def execute(request: TaskRequest):
            task_desc = (request.description or request.task or "").strip()
            if not task_desc:
                raise HTTPException(status_code=422, detail="Missing task")
            task_id = request.id or request.task_id or "unknown"
            context = request.context if isinstance(request.context, dict) else {}
            
            if self.logger:
                self.logger.info("task_received", task_id=task_id)
            
            try:
                result = await self.process_task(task_desc, context, request.requires_approval)
                return {"status": "success", "result": result}
            except Exception as e:
                if self.logger:
                    self.logger.error("task_failed", error=str(e))
                raise HTTPException(status_code=500, detail=str(e))

    async def process_task(self, task: str, context: Optional[Dict[str, Any]], requires_approval: bool):
        """Override this method in specialized agents"""
        context = context or {}
        rag_context = ""
        if self.agent_memory:
            rag_context = self.agent_memory.query_relevant_context(task)
            
        project_context = {}
        if self.project_memory:
            project_context = self.project_memory.get_project_context()

        plan = await self.generate_plan(task, rag_context, project_context)
        
        if requires_approval and self.approval_system:
            approval = await self.approval_system.request_approval(
                self.config.name,
                "execute_task",
                {"task": task, "plan": plan}
            )
            if approval['status'] != "approved":
                raise Exception(f"Task rejected: {approval.get('reason')}")
        
        return f"Executed task: {task} based on plan: {plan}"

    async def generate_plan(self, task, rag_context, project_context):
        if not self.client:
            return "No AI client configured — running in limited mode"

        prompt = f"""
        You are {self.config.name} ({self.config.role}).

        CONTEXT FROM BIBLE:
        {rag_context}

        PROJECT STATUS:
        {project_context}

        TASK:
        {task}

        Create a brief execution plan.
        """

        for attempt in range(4):
            try:
                if ai_backend == "anthropic":
                    response = await self.client.messages.create(
                        model=self.config.model,
                        max_tokens=1000,
                        timeout=30.0,
                        messages=[{"role": "user", "content": prompt}]
                    )
                    return response.content[0].text
                elif ai_backend == "openai":
                    response = await self.client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "user", "content": prompt}],
                        timeout=30.0,
                    )
                    return response.choices[0].message.content
                return "No AI backend available"
            except Exception as e:
                err_str = str(e).lower()
                if attempt < 3 and ("rate" in err_str or "connection" in err_str or "timeout" in err_str):
                    wait = 2 ** (attempt + 1)
                    if self.logger:
                        self.logger.warning(f"AI call failed (attempt {attempt + 1}): {e}. Retry in {wait}s")
                    await asyncio.sleep(wait)
                else:
                    if self.logger:
                        self.logger.error(f"AI API error: {e}")
                    return f"Plan generation failed: {e}"

    def run(self):
        import uvicorn
        uvicorn.run(self.app, host="0.0.0.0", port=self.config.port)
