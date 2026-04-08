"""
Agent X — The Meta-Architect
=============================
HyperCode V2.0's crown jewel. Agent X designs, deploys, and evolves
other agents autonomously using:

  • LLM-powered agent design  (designer.py → Ollama)
  • Evolutionary pipeline      (pipeline.py → detect/improve/deploy)
  • Docker operations          (docker_ops.py → build/restart/rollback)

Port  : 8080
Health: GET /health

Key endpoints:
  GET  /agents                  — list all known agents + live health
  POST /agents/spawn            — design + scaffold a brand new agent
  POST /agents/{name}/evolve    — trigger evolution for one agent
  POST /agents/{name}/rebuild   — rebuild + redeploy without code changes
  POST /pipeline/run            — run full evolutionary cycle (dry_run=true default)
  GET  /pipeline/status         — current or last pipeline run status
  GET  /pipeline/history        — full cycle history
  POST /design/spec             — generate agent spec from description (LLM)
  POST /design/code             — generate full agent code from spec (LLM)
  GET  /llm/status              — check if Ollama is available
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Optional

import uvicorn
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent-x")

# ── Config ────────────────────────────────────────────────────────────────────

AGENT_NAME = os.getenv("AGENT_NAME", "agent-x-01")
AGENT_PORT = int(os.getenv("AGENT_PORT", "8000"))
CREW_URL = os.getenv("CREW_ORCHESTRATOR_URL", "http://crew-orchestrator:8081")
VERSION = "2.0.0"

# ── Import sub-modules ────────────────────────────────────────────────────────────

from agentx.designer import (
    AgentSpec,
    design_agent_spec,
    generate_agent_code,
    ollama_available,
    suggest_improvement,
)
from agentx.docker_ops import (
    COMPOSE_FILE,
    WORKSPACE,
    build_image,
    container_health,
    deploy_service,
    list_containers,
    restart_service,
    write_agent_file,
)
from agentx.pipeline import EvolutionaryPipeline, KNOWN_AGENTS

# ── App + state ───────────────────────────────────────────────────────────────

class SpawnRequest(BaseModel):
    description: str
    auto_deploy: bool = False

class EvolveRequest(BaseModel):
    dry_run: bool = True

class RebuildRequest(BaseModel):
    compose_file: Optional[str] = None

class PipelineRunRequest(BaseModel):
    dry_run: bool = True

class DesignSpecRequest(BaseModel):
    description: str

class DesignCodeRequest(BaseModel):
    spec: dict[str, Any]

class ExecuteTaskRequest(BaseModel):
    id: Optional[str] = None
    task: Optional[str] = None
    type: str = "generic"
    context: Optional[dict[str, Any]] = None

class AgentX:
    def __init__(self):
        self.start_time = time.time()
        self.pipeline: EvolutionaryPipeline | None = None
        self.spawn_history: list[dict[str, Any]] = []
        self.app = FastAPI(
            title="Agent X — Meta-Architect",
            description=(
                "HyperCode V2.0 Meta-Architect. Designs, deploys, and evolves AI agents "
                "autonomously using LLM-powered design and Docker operations."
            ),
            version=VERSION,
            lifespan=self.lifespan,
        )
        self.setup_routes()

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        """Modern FastAPI lifespan — replaces deprecated on_event handlers."""
        # ── STARTUP ──
        self.pipeline = EvolutionaryPipeline()
        logger.info(f"[Agent X] Starting up on port {AGENT_PORT}...")

        import httpx
        payload = {
            "name": AGENT_NAME,
            "archetype": "architect",
            "version": VERSION,
            "port": AGENT_PORT,
            "health_url": f"http://agent-x:{AGENT_PORT}/health",
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(f"{CREW_URL}/agents/register", json=payload)
                logger.info(f"[Agent X] Registered with Crew: {resp.status_code}")
        except Exception as exc:
            logger.warning(f"[Agent X] Crew registration pending: {exc}")

        llm_ready = await ollama_available()
        logger.info(f"[Agent X] Ready. LLM={llm_ready}")

        yield  # ← app runs here

        # ── SHUTDOWN ──
        logger.info("[Agent X] Shutting down.")

    def get_pipeline(self) -> EvolutionaryPipeline:
        """Safe accessor — pipeline is ready after lifespan startup."""
        if self.pipeline is None:
            raise HTTPException(status_code=503, detail="Pipeline not initialised yet.")
        return self.pipeline

    def setup_routes(self):
        app = self.app
        
        # ── Standard health / info routes ─────────────────────────────────────────────────

        @app.get("/health")
        async def health() -> dict[str, Any]:
            return {
                "name": AGENT_NAME,
                "archetype": "architect",
                "status": "ready",
                "version": VERSION,
                "uptime_seconds": round(time.time() - self.start_time, 2),
                "message": f"{AGENT_NAME} is ready. All systems operational.",
            }

        @app.get("/info")
        async def info() -> dict[str, Any]:
            return {
                "name": AGENT_NAME,
                "archetype": "architect",
                "version": VERSION,
                "port": AGENT_PORT,
                "status": "ready",
                "hypercode_version": "2.0",
                "capabilities": [
                    "agent_design",
                    "agent_spawn",
                    "evolutionary_pipeline",
                    "docker_build_deploy",
                    "llm_code_generation",
                ],
            }

        @app.post("/execute")
        async def execute(req: ExecuteTaskRequest) -> dict[str, Any]:
            task_type = (req.type or "generic").strip().lower()
            ctx = req.context or {}

            if task_type == "spawn_agent":
                description = ctx.get("description") or req.task
                if not description:
                    raise HTTPException(status_code=422, detail="Missing description for spawn_agent")

                auto_deploy = bool(ctx.get("auto_deploy", False))
                spec = await design_agent_spec(description)
                generated = await generate_agent_code(spec)

                files_written = {}
                try:
                    main_path = write_agent_file(f"agents/{spec.name}/main.py", generated.code)
                    req_path = write_agent_file(f"agents/{spec.name}/requirements.txt", generated.requirements)
                    df_path = write_agent_file(f"agents/{spec.name}/Dockerfile", generated.dockerfile)
                    files_written = {
                        "main_py": main_path,
                        "requirements_txt": req_path,
                        "dockerfile": df_path,
                    }
                except ValueError as exc:
                    raise HTTPException(status_code=400, detail=str(exc))

                record: dict[str, Any] = {
                    "task_id": req.id,
                    "spec": {
                        "name": spec.name,
                        "container_name": spec.container_name,
                        "port": spec.port,
                        "archetype": spec.archetype,
                        "purpose": spec.purpose,
                        "capabilities": spec.capabilities,
                        "endpoints": spec.endpoints,
                    },
                    "files_written": files_written,
                    "llm_used": generated.llm_used,
                    "warnings": generated.warnings,
                    "auto_deploy": auto_deploy,
                    "spawned_at": time.time(),
                }

                if auto_deploy:
                    asyncio.create_task(self._background_build_deploy(spec, record))
                    record["deploy_status"] = "queued"
                else:
                    record["deploy_status"] = "not_requested"

                self.spawn_history.append(record)
                return record

            if task_type == "evolve":
                name = ctx.get("name")
                dry_run = bool(ctx.get("dry_run", True))
                if not name:
                    raise HTTPException(status_code=422, detail="Missing agent name for evolve")

                improvement = await suggest_improvement(name, "# Source code not provided", {})
                return {
                    "task_id": req.id,
                    "agent": name,
                    "dry_run": dry_run,
                    "improvement": improvement,
                    "timestamp": time.time(),
                }

            raise HTTPException(status_code=422, detail="Unsupported task type for Agent X")

        # ── Agent registry & health ─────────────────────────────────────────────────────

        @app.get("/agents")
        async def list_agents() -> dict[str, Any]:
            """List all known agents with live container health."""
            import httpx

            results = []
            async with httpx.AsyncClient() as client:
                for manifest in KNOWN_AGENTS:
                    try:
                        resp = await client.get(manifest["health_url"], timeout=3.0)
                        health_data = resp.json() if resp.status_code == 200 else {}
                        reachable = resp.status_code == 200
                    except Exception:
                        health_data = {}
                        reachable = False

                    results.append({
                        "name": manifest["name"],
                        "container": manifest["container_name"],
                        "reachable": reachable,
                        "status": health_data.get("status", "unknown"),
                        "uptime_seconds": health_data.get("uptime_seconds"),
                        "health_url": manifest["health_url"],
                    })

            return {
                "agents": results,
                "total": len(results),
                "healthy": sum(1 for a in results if a["reachable"]),
            }

        @app.get("/agents/{name}/status")
        async def agent_status(name: str) -> dict[str, Any]:
            """Detailed health + stats for a specific agent."""
            import httpx

            manifest = next((m for m in KNOWN_AGENTS if m["name"] == name), None)
            if not manifest:
                raise HTTPException(status_code=404, detail=f"Agent '{name}' not in registry.")

            result: dict[str, Any] = {"name": name, "manifest": manifest}

            async with httpx.AsyncClient() as client:
                for endpoint_type, url_key in [("health", "health_url"), ("stats", "stats_url")]:
                    try:
                        resp = await client.get(manifest[url_key], timeout=3.0)
                        result[endpoint_type] = resp.json() if resp.status_code == 200 else {}
                    except Exception as exc:
                        result[endpoint_type] = {"error": str(exc)}

            docker_health = await container_health(manifest["container_name"])
            result["docker"] = docker_health
            return result

        # ── Agent spawning ─────────────────────────────────────────────────────────────────

        @app.post("/agents/spawn", status_code=202)
        async def spawn_agent(req: SpawnRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
            spec = await design_agent_spec(req.description)
            generated = await generate_agent_code(spec)

            files_written = {}
            try:
                main_path = write_agent_file(f"agents/{spec.name}/main.py", generated.code)
                req_path = write_agent_file(f"agents/{spec.name}/requirements.txt", generated.requirements)
                df_path = write_agent_file(f"agents/{spec.name}/Dockerfile", generated.dockerfile)
                files_written = {
                    "main_py": main_path,
                    "requirements_txt": req_path,
                    "dockerfile": df_path,
                }
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))

            record: dict[str, Any] = {
                "spec": {
                    "name": spec.name,
                    "container_name": spec.container_name,
                    "port": spec.port,
                    "archetype": spec.archetype,
                    "purpose": spec.purpose,
                    "capabilities": spec.capabilities,
                    "endpoints": spec.endpoints,
                },
                "files_written": files_written,
                "llm_used": generated.llm_used,
                "warnings": generated.warnings,
                "auto_deploy": req.auto_deploy,
                "spawned_at": time.time(),
            }

            if req.auto_deploy:
                background_tasks.add_task(self._background_build_deploy, spec, record)
                record["deploy_status"] = "queued"
            else:
                record["deploy_status"] = "not_requested"
                record["next_step"] = (
                    f"Run: docker compose -f docker-compose.hyper-agents.yml "
                    f"up -d --build {spec.container_name}"
                )

            self.spawn_history.append(record)
            return record

        @app.get("/agents/spawn/history")
        async def spawn_history() -> dict[str, Any]:
            return {"spawned": self.spawn_history, "total": len(self.spawn_history)}

        # ── Agent evolution ─────────────────────────────────────────────────────────────────

        @app.post("/agents/{name}/evolve")
        async def evolve_agent(name: str, req: EvolveRequest) -> dict[str, Any]:
            manifest = next((m for m in KNOWN_AGENTS if m["name"] == name), None)
            if not manifest:
                raise HTTPException(status_code=404, detail=f"Agent '{name}' not in registry.")

            code_path = f"{WORKSPACE}/{manifest['code_path']}"
            try:
                with open(code_path, encoding="utf-8") as f:
                    current_code = f.read()
            except OSError:
                current_code = "# Source code not accessible in container"

            import httpx
            stats: dict[str, Any] = {}
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(manifest["stats_url"], timeout=3.0)
                    if resp.status_code == 200:
                        stats = resp.json()
            except Exception:
                pass

            improvement = await suggest_improvement(name, current_code, stats)
            pipeline = self.get_pipeline()

            result: dict[str, Any] = {
                "agent": name,
                "dry_run": req.dry_run,
                "improvement": improvement,
                "timestamp": time.time(),
            }

            if not req.dry_run:
                scores = await pipeline.scan()
                agent_score = next((s for s in scores if s.name == name), None)
                if agent_score:
                    result["current_score"] = agent_score.score
                    result["issues"] = agent_score.issues

                build = await build_image(
                    name=name,
                    version=f"evolved-{int(time.time())}",
                    dockerfile_path=f"{WORKSPACE}/{manifest['dockerfile']}",
                    context_path=WORKSPACE,
                )
                result["build"] = {
                    "success": build.success,
                    "image_tag": build.image_tag,
                    "error": build.error,
                }

                if build.success:
                    from agentx.docker_ops import wait_for_healthy
                    deploy = await deploy_service(
                        service_name=manifest["service_name"],
                        compose_file=COMPOSE_FILE,
                    )
                    healthy = await wait_for_healthy(manifest["container_name"], timeout_seconds=60)
                    result["deploy"] = {
                        "success": deploy.success,
                        "healthy_after": healthy,
                        "error": deploy.error,
                    }

            return result

        @app.post("/agents/{name}/rebuild")
        async def rebuild_agent(name: str, req: RebuildRequest) -> dict[str, Any]:
            manifest = next((m for m in KNOWN_AGENTS if m["name"] == name), None)
            if not manifest:
                raise HTTPException(status_code=404, detail=f"Agent '{name}' not in registry.")

            compose_file = req.compose_file or COMPOSE_FILE
            deploy = await deploy_service(
                service_name=manifest["service_name"],
                compose_file=compose_file,
                build=True,
            )
            return {
                "agent": name,
                "success": deploy.success,
                "old_image": deploy.old_image,
                "new_image": deploy.new_image,
                "error": deploy.error,
            }

        # ── Evolutionary pipeline ──────────────────────────────────────────────────────────

        @app.post("/pipeline/run")
        async def run_pipeline(req: PipelineRunRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
            pipeline = self.get_pipeline()
            if pipeline.is_running:
                raise HTTPException(
                    status_code=409,
                    detail="Pipeline already running. Check /pipeline/status for progress.",
                )
            background_tasks.add_task(pipeline.run_cycle, req.dry_run)
            return {
                "status": "started",
                "dry_run": req.dry_run,
                "message": "Pipeline running in background. Poll GET /pipeline/status for progress.",
            }

        @app.get("/pipeline/status")
        async def pipeline_status() -> dict[str, Any]:
            return self.get_pipeline().current_status()

        @app.get("/pipeline/history")
        async def pipeline_history() -> dict[str, Any]:
            pipeline = self.get_pipeline()
            return {
                "cycles": [r.summary() for r in pipeline.history],
                "total": len(pipeline.history),
            }

        @app.post("/pipeline/scan")
        async def scan_agents() -> dict[str, Any]:
            scores = await self.get_pipeline().scan()
            return {
                "scores": [
                    {
                        "name": s.name,
                        "score": s.score,
                        "reachable": s.reachable,
                        "healthy": s.healthy,
                        "needs_attention": s.needs_attention,
                        "issues": s.issues,
                    }
                    for s in scores
                ],
                "healthy_count": sum(1 for s in scores if not s.needs_attention),
                "flagged_count": sum(1 for s in scores if s.needs_attention),
                "threshold": 60,
            }

        # ── LLM design tools ───────────────────────────────────────────────────────────────

        @app.post("/design/spec")
        async def design_spec(req: DesignSpecRequest) -> dict[str, Any]:
            spec = await design_agent_spec(req.description)
            return {
                "name": spec.name,
                "container_name": spec.container_name,
                "port": spec.port,
                "archetype": spec.archetype,
                "purpose": spec.purpose,
                "capabilities": spec.capabilities,
                "endpoints": spec.endpoints,
                "dependencies": spec.dependencies,
                "suggested_handlers": spec.suggested_handlers,
                "llm_used": spec.llm_used,
            }

        @app.post("/design/code")
        async def design_code(req: DesignCodeRequest) -> dict[str, Any]:
            spec = AgentSpec(
                name=req.spec.get("name", "custom-agent"),
                container_name=req.spec.get("container_name", "hyper-custom"),
                port=int(req.spec.get("port", 8094)),
                archetype=req.spec.get("archetype", "worker"),
                purpose=req.spec.get("purpose", "Custom agent"),
                capabilities=req.spec.get("capabilities", []),
                endpoints=req.spec.get("endpoints", []),
                dependencies=req.spec.get("dependencies", []),
                suggested_handlers=req.spec.get("suggested_handlers", []),
            )
            generated = await generate_agent_code(spec)
            return {
                "agent_name": generated.agent_name,
                "code": generated.code,
                "dockerfile": generated.dockerfile,
                "requirements": generated.requirements,
                "llm_used": generated.llm_used,
                "warnings": generated.warnings,
            }

        @app.get("/design/code/{name}", response_class=PlainTextResponse)
        async def get_agent_code(name: str) -> str:
            manifest = next((m for m in KNOWN_AGENTS if m["name"] == name), None)
            if not manifest:
                raise HTTPException(status_code=404, detail=f"Agent '{name}' not in registry.")
            code_path = f"{WORKSPACE}/{manifest['code_path']}"
            try:
                with open(code_path, encoding="utf-8") as f:
                    return f.read()
            except OSError:
                raise HTTPException(status_code=503, detail="Source code not accessible in container.")

        # ── LLM status ─────────────────────────────────────────────────────────────────────

        @app.get("/llm/status")
        async def llm_status() -> dict[str, Any]:
            import httpx
            from agentx.designer import OLLAMA_HOST, OLLAMA_MODEL

            available = await ollama_available()
            models: list[str] = []

            if available:
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        resp = await client.get(f"{OLLAMA_HOST}/api/tags")
                        if resp.status_code == 200:
                            data = resp.json()
                            models = [m["name"] for m in data.get("models", [])]
                except Exception:
                    pass

            return {
                "ollama_host": OLLAMA_HOST,
                "available": available,
                "configured_model": OLLAMA_MODEL,
                "loaded_models": models,
                "model_ready": OLLAMA_MODEL in models or any(OLLAMA_MODEL.split(":")[0] in m for m in models),
            }

        # ── Docker inventory ───────────────────────────────────────────────────────────────

        @app.get("/docker/containers")
        async def docker_containers() -> dict[str, Any]:
            containers = await list_containers()
            hypercode_containers = await list_containers(label="hypercode.agent=true")
            return {
                "all_containers": containers,
                "hypercode_agents": hypercode_containers,
                "total": len(containers),
                "hypercode_total": len(hypercode_containers),
            }

        @app.get("/docker/health/{container_name}")
        async def docker_container_health(container_name: str) -> dict[str, Any]:
            return await container_health(container_name)

    async def _background_build_deploy(self, spec: AgentSpec, record: dict[str, Any]) -> None:
        build_result = await build_image(
            name=spec.name,
            version="v1.0.0",
            dockerfile_path=f"{WORKSPACE}/agents/{spec.name}/Dockerfile",
            context_path=WORKSPACE,
        )
        record["build"] = {
            "success": build_result.success,
            "image_tag": build_result.image_tag,
            "duration_seconds": build_result.duration_seconds,
            "error": build_result.error,
        }
        record["deploy_status"] = "built_ready_to_deploy" if build_result.success else "build_failed"


# ── Entry ─────────────────────────────────────────────────────────────────────

agent_x = AgentX()
app = agent_x.app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=AGENT_PORT, log_level="info")
