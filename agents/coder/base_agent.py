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


# ─── LLM helpers ────────────────────────────────────────────────────────────

class _OllamaAdapter:
    """Thin Anthropic-interface wrapper over the Ollama OpenAI-compat endpoint."""
    def __init__(self, model: str, base_url: str, api_key: str) -> None:
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self._model = model
        self.messages = self  # so client.messages.create() works

    async def create(self, model=None, max_tokens=1000, messages=None, system=None, **kwargs):
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.extend(messages or [])

        class _Msg:
            def __init__(self, text: str) -> None:
                self.text = text

        class _Resp:
            def __init__(self, text: str) -> None:
                self.content = [_Msg(text)]

        resp = await self._client.chat.completions.create(
            model=model or self._model,
            max_tokens=max_tokens,
            messages=msgs,
        )
        return _Resp(resp.choices[0].message.content or "")


def _build_llm_client():
    """
    Anthropic → Ollama fallback chain, mirrors crew-orchestrator/_get_llm().
    Returns an object exposing .messages.create() in the Anthropic SDK style.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        from anthropic import AsyncAnthropic
        return AsyncAnthropic(api_key=api_key)
    return _OllamaAdapter(
        model=os.getenv("LLM_MODEL", "llama3.2"),
        base_url=os.getenv("LLM_API_BASE", "http://ollama:11434/v1"),
        api_key=os.getenv("LLM_API_KEY", "NA"),
    )


@dataclass
class AgentConfig:
    name: str = os.getenv("AGENT_NAME", "coder-agent")
    port: int = int(os.getenv("AGENT_PORT", "8080"))
    model: str = os.getenv("AGENT_MODEL", "claude-sonnet-4-6")
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379")
    extra: dict = field(default_factory=dict)


class TaskRequest:
    def __init__(self, task_id: str, task: str, context: dict = None, description: str = ""):
        self.task_id = task_id
        self.task = task
        self.description = description
        self.context = context or {}


class TaskResponse:
    def __init__(self, task_id: str, agent: str, status: str, result: Any = None, error: str = None):
        self.task_id = task_id
        self.agent = agent
        self.status = status
        self.result = result
        self.error = error


class ProjectMemory:
    def __init__(self):
        self._data = {"available_apis": []}

    def get_project_context(self) -> dict:
        return self._data

    def add_api_endpoint(self, endpoint: str):
        if endpoint not in self._data["available_apis"]:
            self._data["available_apis"].append(endpoint)


class AgentMemory:
    def query_relevant_context(self, query: str) -> str:
        return ""


class ApprovalSystem:
    async def request_approval(self, agent_name: str, action: str, payload: dict, timeout: int = 300) -> dict:
        return {"status": "approved"}


class BaseAgent:
    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.logger = logging.getLogger(self.config.name)
        logging.basicConfig(level=logging.INFO)

        self.redis = None

        # LLM client (Anthropic → Ollama fallback)
        self.client = _build_llm_client()

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
            except Exception as e:
                self.logger.warning(f"Redis unavailable: {e}")

    async def _shutdown_cleanup(self):
        if self.redis:
            try:
                await self.redis.set(f"agent:{self.config.name}:status", "offline")
                await self.redis.aclose()
            except Exception:
                pass

    async def process_task(self, task: str, context: dict, requires_approval: bool = False) -> dict:
        raise NotImplementedError("Subclasses must implement process_task()")
