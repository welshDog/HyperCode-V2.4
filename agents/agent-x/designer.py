"""
Agent X — LLM Agent Designer
==============================
Uses the local Ollama instance (OpenAI-compatible API) to design,
improve, and generate Python FastAPI agent code.

Falls back gracefully if Ollama is unreachable — always returns
a structured response so callers don't crash.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://hypercode-ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:3b")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT_SECONDS", "120"))

# ── Prompts (qwen2.5-coder optimised: short, direct, JSON-only) ─────────────────

_SYSTEM_PROMPT = "You are a Python FastAPI agent code generator. Output only what is asked. No explanations."

_DESIGN_SPEC_PROMPT = """Output only a JSON object for this agent: {description}
Fields: name, container_name, port (8094-8099), archetype (worker/observer/architect), purpose, capabilities (list), endpoints (list), dependencies (list)
JSON only. No other text."""

_CODE_GEN_PROMPT = """Write a Python FastAPI agent.
Name: {name} Port: {port} Archetype: {archetype} Purpose: {purpose}
Must have: /health endpoint, execute() method, uvicorn entry point.
Python code only. No markdown."""

_IMPROVE_PROMPT = """Agent: {agent_name}
Issue: {issue}
Metrics: {metrics}

Respond with ONLY this JSON (no other text):
{{"issue": "one line problem", "improvement": "one line fix", "impact": "one line benefit", "code_diff": "key code change or empty string"}}"""


# ── LLM client ────────────────────────────────────────────────────────────────

async def _ollama_generate(prompt: str, system: str = _SYSTEM_PROMPT) -> str:
    """Call Ollama generate API. Returns raw text or empty string."""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": f"{system}\n\n{prompt}",
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 512,
            "stop": ["\n\n\n"],
        },
    }
    try:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
            resp = await client.post(f"{OLLAMA_HOST}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")
    except httpx.ConnectError:
        logger.warning("[Designer] Ollama unreachable — returning fallback response")
        return ""
    except Exception as exc:
        logger.error(f"[Designer] LLM call failed: {exc!r}")
        return ""


async def _ollama_chat(messages: list[dict[str, str]]) -> str:
    """Call Ollama chat API for multi-turn conversations."""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 512},
    }
    try:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
            resp = await client.post(f"{OLLAMA_HOST}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")
    except Exception as exc:
        logger.error(f"[Designer] LLM chat failed: {exc!r}")
        return ""


async def ollama_available() -> bool:
    """Quick check if Ollama is reachable."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OLLAMA_HOST}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False


# ── Public API ────────────────────────────────────────────────────────────────

@dataclass
class AgentSpec:
    name: str
    container_name: str
    port: int
    archetype: str
    purpose: str
    capabilities: list[str] = field(default_factory=list)
    endpoints: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    suggested_handlers: list[str] = field(default_factory=list)
    llm_used: bool = False


@dataclass
class GeneratedCode:
    agent_name: str
    code: str
    dockerfile: str
    requirements: str
    llm_used: bool = False
    warnings: list[str] = field(default_factory=list)


async def design_agent_spec(description: str) -> AgentSpec:
    """Ask the LLM to design an agent spec from a plain-English description."""
    import json, re

    prompt = _DESIGN_SPEC_PROMPT.format(description=description)
    raw = await _ollama_generate(prompt)

    if raw:
        json_match = re.search(r'\{.*?\}', raw, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return AgentSpec(
                    name=data.get("name", "custom-agent"),
                    container_name=data.get("container_name", f"hyper-{data.get('name', 'custom')}"),
                    port=int(data.get("port", 8094)),
                    archetype=data.get("archetype", "worker"),
                    purpose=data.get("purpose", description),
                    capabilities=data.get("capabilities", []),
                    endpoints=data.get("endpoints", ["/health", "/execute"]),
                    dependencies=data.get("dependencies", []),
                    suggested_handlers=data.get("suggested_handlers", []),
                    llm_used=True,
                )
            except (json.JSONDecodeError, KeyError) as exc:
                logger.warning(f"[Designer] Failed to parse LLM spec JSON: {exc}")

    # Fallback
    name = description.lower().replace(" ", "-")[:30].strip("-")
    return AgentSpec(
        name=name,
        container_name=f"hyper-{name}",
        port=8094,
        archetype="worker",
        purpose=description,
        capabilities=["Execute tasks", "Health reporting", "Crew registration"],
        endpoints=["/health", "/info", "/execute", "/stats"],
        dependencies=["redis", "crew-orchestrator"],
        llm_used=False,
    )


async def generate_agent_code(spec: AgentSpec) -> GeneratedCode:
    """Generate full Python agent code from a spec."""
    prompt = _CODE_GEN_PROMPT.format(
        name=spec.name,
        port=spec.port,
        archetype=spec.archetype,
        purpose=spec.purpose,
    )
    code = await _ollama_generate(prompt)

    if not code or len(code) < 100:
        code = _boilerplate(spec)
        llm_used = False
        warnings = ["Ollama unavailable — boilerplate template used"]
    else:
        llm_used = True
        warnings = []

    return GeneratedCode(
        agent_name=spec.name,
        code=code,
        dockerfile=_dockerfile_template(spec),
        requirements=_requirements_template(),
        llm_used=llm_used,
        warnings=warnings,
    )


async def suggest_improvement(
    agent_name: str,
    current_code: str,
    performance_data: dict[str, Any],
) -> dict[str, Any]:
    """Ask LLM to suggest one specific improvement for an agent."""
    import json, re

    issue = performance_data.get("issues", ["unknown issue"])
    issue_str = issue[0] if issue else "performance degradation"
    metrics = {
        "score": performance_data.get("score", 0),
        "success_rate": performance_data.get("success_rate", 0),
        "error_count": performance_data.get("error_count", 0),
    }

    prompt = _IMPROVE_PROMPT.format(
        agent_name=agent_name,
        issue=issue_str,
        metrics=str(metrics),
    )
    raw = await _ollama_generate(prompt)

    if raw:
        json_match = re.search(r'\{[^{}]*\}', raw, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group())
                if "issue" in result and "improvement" in result:
                    logger.info(f"[Designer] LLM improvement generated for {agent_name}")
                    return result
            except json.JSONDecodeError as exc:
                logger.warning(f"[Designer] JSON parse failed: {exc} | raw: {raw[:200]}")

    logger.warning(f"[Designer] LLM returned no usable JSON for {agent_name}")
    return {
        "issue": "LLM analysis unavailable",
        "improvement": "Ensure Ollama is running and has a model loaded",
        "impact": "None — manual review required",
        "code_diff": "",
    }


# ── Code templates ────────────────────────────────────────────────────────────────

def _boilerplate(spec: AgentSpec) -> str:
    class_name = "".join(w.capitalize() for w in spec.name.replace("-", "_").split("_")) + "Agent"
    return f'''\
"""
HyperCode V2.0 — {spec.name} Agent
{'=' * (len(spec.name) + 28)}
{spec.purpose}

Port  : {spec.port}
Health: GET /health
"""
from __future__ import annotations

import os
from typing import Any

import uvicorn
from src.agents.hyper_agents import AgentArchetype
from src.agents.hyper_agents.base_agent import HyperAgent

AGENT_NAME = os.getenv("AGENT_NAME", "{spec.name}-01")
AGENT_PORT = int(os.getenv("AGENT_PORT", "{spec.port}"))
CREW_URL = os.getenv("CREW_ORCHESTRATOR_URL", "http://crew-orchestrator:8081")


class {class_name}(HyperAgent):
    """{spec.purpose}"""

    async def execute(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task.get("action", "status")
        return {{"status": "ok", "action": action, "agent": self.name}}


agent = {class_name}(
    name=AGENT_NAME,
    archetype=AgentArchetype.{spec.archetype.upper()},
    port=AGENT_PORT,
)
app = agent.app


@app.get("/stats")
async def stats() -> dict[str, Any]:
    return {{"name": agent.name, "status": agent.status.value}}


@app.post("/execute")
async def execute(task: dict[str, Any]) -> dict[str, Any]:
    return await agent.execute(task)


@app.on_event("startup")
async def startup() -> None:
    agent.set_ready()
    agent.register_with_crew(crew_url=CREW_URL)


@app.on_event("shutdown")
async def shutdown() -> None:
    agent.shutdown()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=AGENT_PORT, log_level="info")
'''


def _dockerfile_template(spec: AgentSpec) -> str:
    return f'''\
# Stage 1: Build
FROM python:3.11.8-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
COPY agents/{spec.name}/requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels -r requirements.txt

# Stage 2: Runtime
FROM python:3.11.8-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app \\
    AGENT_NAME={spec.name}-01 AGENT_PORT={spec.port}
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/*
COPY src/agents/hyper_agents/ /app/src/agents/hyper_agents/
RUN mkdir -p /app/src/agents && touch /app/src/__init__.py /app/src/agents/__init__.py
COPY agents/{spec.name}/main.py /app/main.py
EXPOSE {spec.port}
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=20s \\
    CMD curl -f http://localhost:{spec.port}/health || exit 1
CMD ["python", "main.py"]
'''


def _requirements_template() -> str:
    return (
        "fastapi==0.116.1\n"
        "uvicorn[standard]==0.34.3\n"
        "pydantic==2.9.2\n"
        "httpx==0.28.1\n"
    )
