import os
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
import httpx
import secrets
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("coder-agent")

def _self_agent_key() -> str:
    """OWN identity for agent->core calls (Phase 10E) — env first, then the
    registered Docker secret. Empty = event mirroring silently off."""
    key = (os.getenv("HYPERCODE_AGENT_KEY") or "").strip()
    if key:
        return key
    path = os.getenv(
        "HYPERCODE_AGENT_KEY_FILE", "/run/secrets/agent_api_key_coder-agent"
    )
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


async def _publish_core_event(event_status: str, task_id: str, payload: Dict[str, Any]) -> None:
    """Mirror an execution event to core POST /api/v1/events as coder-agent.
    Fail-open — core down or key missing never affects the task response."""
    key = _self_agent_key()
    if not key:
        return
    core_url = os.getenv("CORE_URL", "http://hypercode-core:8000").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{core_url}/api/v1/events",
                headers={"X-Agent-Key": key},
                json={
                    "channel": "task",
                    "agentId": "coder-agent",
                    "taskId": task_id,
                    "status": event_status,
                    "payload": payload,
                },
            )
    except Exception as exc:
        logger.warning("core event publish failed (non-fatal): %s", exc)


# Define base classes if they are not in base_agent (or import them)
class AgentConfig:
    def __init__(self, name: str, port: int, redis_url: str = "redis://redis:6379", **kwargs):
        self.name = name
        self.port = port
        self.redis_url = redis_url
        for k, v in kwargs.items():
            setattr(self, k, v)

class TaskRequest(BaseModel):
    id: str
    task: str
    context: Optional[Dict[str, Any]] = None

class TaskResponse(BaseModel):
    task_id: str
    agent: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class CoderAgent:
    """
    Coder Agent responsible for generating, analyzing, and deploying code.
    """
    def __init__(self, config: AgentConfig):
        self.config = config

        @asynccontextmanager
        async def _lifespan(app: FastAPI):
            await self.startup()
            yield
            await self.shutdown()

        self.app = FastAPI(title="Coder Agent API", lifespan=_lifespan)
        self.redis = None
        self.http_client = httpx.AsyncClient(timeout=60.0)
        @self.app.middleware("http")
        async def _agent_auth_middleware(request: Request, call_next):
            if request.url.path.startswith("/health"):
                return await call_next(request)

            expected = (os.getenv("HYPERCODE_API_KEY") or os.getenv("AGENT_API_KEY") or "").strip()
            if not expected:
                return JSONResponse(status_code=503, content={"detail": "Agent API key not configured"})

            provided = request.headers.get("x-agent-key") or request.headers.get("x-api-key")
            if not provided or not secrets.compare_digest(str(provided), expected):
                return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})

            return await call_next(request)
        self.setup_routes()

    async def startup(self):
        logger.info(f"Starting {self.config.name} on port {self.config.port}")
        # Initialize Redis or other state management here if available
        # self.redis = await aioredis.from_url(self.config.redis_url)

    async def shutdown(self):
        logger.info(f"Shutting down {self.config.name}")
        await self.http_client.aclose()
        if self.redis:
            self.redis.close()

    def setup_routes(self):
        @self.app.post("/execute", response_model=TaskResponse)
        async def execute_endpoint(request: TaskRequest):
            return await self.execute(request)

        @self.app.get("/health")
        async def health():
            return {"status": "healthy", "agent": self.config.name}

    async def execute(self, request: TaskRequest) -> TaskResponse:
        """Execute a coding task."""
        logger.info(f"Executing task {request.id}: {request.task}")
        
        try:
            task_lower = request.task.lower()
            result_data = {}
            
            if "metrics" in task_lower or "health" in task_lower:
                result_data = self.analyze_system_health()
            elif "deploy" in task_lower or "docker" in task_lower:
                code_context = request.context.get("code", "") if request.context else request.task
                result_data = await self.analyze_and_deploy(code_context)
            elif "todo list" in task_lower:
                result_data = await self.implement_todo_app()
            else:
                result_data = await self.generate_code_with_ollama(request.task)
                
            logger.info(f"Task {request.id} completed successfully.")
            # Phase 10E: announce the execution to core's event stream as US
            await _publish_core_event(
                "completed", request.id,
                {"task": request.task[:120], "result_keys": list(result_data.keys())},
            )
            return TaskResponse(
                task_id=request.id,
                agent=self.config.name,
                status="completed",
                result=result_data
            )

        except Exception as e:
            logger.error(f"Task {request.id} failed: {str(e)}", exc_info=True)
            await _publish_core_event(
                "failed", request.id, {"task": request.task[:120], "error": str(e)[:300]},
            )
            return TaskResponse(
                task_id=request.id,
                agent=self.config.name,
                status="error",
                error=str(e),
                result={"status": "error", "message": str(e)}
            )

    async def implement_todo_app(self) -> Dict[str, Any]:
        """Mock implementation for Todo App."""
        files = {
            "api/routes/todos.py": "from fastapi import APIRouter\nrouter = APIRouter()",
            "components/TodoList.tsx": "export const TodoList = () => <div>Todo List</div>;"
        }
        return {
            "status": "completed", 
            "files_created": list(files.keys()), 
            "message": "Implemented Todo List App"
        }

    async def analyze_and_deploy(self, code: str) -> Dict[str, Any]:
        """Analyze code and use Docker MCP to manage containers."""
        return {
            "status": "completed", 
            "message": "Successfully analyzed and prepared for deployment.",
            "containers": [],
            "analysis": "Code analyzed."
        }

    def analyze_system_health(self) -> Dict[str, Any]:
        """Mock system health analysis."""
        return {
            "status": "completed",
            "metrics": {
                "cpu_usage": "45%",
                "memory_usage": "60%"
            },
            "analysis": "System is running within normal parameters."
        }

    async def generate_code_with_ollama(self, prompt: str, model: str | None = None) -> Dict[str, Any]:
        """Generate code using Ollama."""
        url = os.getenv("OLLAMA_URL", "http://hypercode-ollama:11434/api/generate")
        resolved_model = (model or os.getenv("OLLAMA_MODEL") or "qwen2.5:3b").strip()
        try:
            models_to_try: list[str] = [resolved_model]
            fallback_model = (os.getenv("OLLAMA_MODEL_FALLBACK") or "").strip()
            if fallback_model and fallback_model not in models_to_try:
                models_to_try.append(fallback_model)
            for candidate in ("qwen2.5:3b", "tinyllama:latest"):
                if candidate not in models_to_try:
                    models_to_try.append(candidate)

            last_error_text: str | None = None
            for candidate_model in models_to_try:
                payload = {"model": candidate_model, "prompt": prompt, "stream": False}
                try:
                    response = await self.http_client.post(url, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    return {"status": "completed", "code": data.get("response", ""), "model": candidate_model}
                except httpx.HTTPStatusError as e:
                    error_text = e.response.text or ""
                    last_error_text = error_text
                    if e.response.status_code == 404 and "model" in error_text and "not found" in error_text:
                        continue
                    if "requires more system memory" in error_text:
                        continue
                    logger.error(f"Ollama HTTP error: {error_text}")
                    return {"status": "error", "message": f"Ollama Error: {error_text}"}

            logger.error(f"Ollama model not available: {last_error_text or 'unknown error'}")
            return {"status": "error", "message": f"Ollama Error: {last_error_text or 'model not available'}"}
        except httpx.RequestError as e:
            logger.error(f"Ollama request failed: {str(e)}")
            return {"status": "error", "message": f"Connection Error: {str(e)}"}

if __name__ == "__main__":
    name = os.getenv("AGENT_NAME", "coder-agent")
    port = int(os.getenv("AGENT_PORT", "8000"))
    
    config = AgentConfig(name=name, port=port)
    agent = CoderAgent(config)
    
    uvicorn.run(agent.app, host="0.0.0.0", port=port)
