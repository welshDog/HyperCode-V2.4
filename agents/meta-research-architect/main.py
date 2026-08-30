#!/usr/bin/env python3
"""Meta-Research Architect Hyper Agent - Phase 1 (observe -> explain).

What it does: on a timer (default weekly) it polls arXiv for new papers in the
configured categories, de-dups against a Redis seen-set, and fans a short brief
out to Redis / Discord / the Obsidian vault. Plus two on-demand endpoints.

What it deliberately cannot do: write to GitHub, touch infrastructure, dispatch
agents, or propose changes on its own. Proposals go through mission-director.
"""

from __future__ import annotations

import contextlib
import logging

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException

import config
import scheduler
import sweep
from models import BriefResult, ResearchBriefRequest

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("meta-research-architect")


@contextlib.asynccontextmanager
async def lifespan(_app: FastAPI):
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown()


app = FastAPI(
    title="Meta-Research Architect Hyper Agent",
    description="Observe -> explain research agent for the HyperCode ecosystem (Phase 1).",
    version=config.VERSION,
    lifespan=lifespan,
)


async def require_key(x_agent_key: str | None = Header(default=None)) -> None:
    """Optional shared-secret gate. No key configured -> open (local dev)."""
    if config.AGENT_API_KEY and x_agent_key != config.AGENT_API_KEY:
        raise HTTPException(status_code=401, detail="invalid or missing X-Agent-Key")


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "agent": config.AGENT_NAME, "phase": config.PHASE}


@app.get("/status")
async def status() -> dict:
    return {
        "agent": config.AGENT_NAME,
        "version": config.VERSION,
        "phase": config.PHASE,
        "sweep": {
            "interval_seconds": config.UPDATE_INTERVAL_SECONDS,
            "categories": config.ARXIV_CATEGORIES,
            "next_run": scheduler.next_run(),
        },
        "sinks": {
            "redis": config.REDIS_URL,
            "discord": bool(config.DISCORD_WEBHOOK_URL),
            "vault": config.VAULT_DIR or None,
        },
        "safety": {
            "observe_only": config.OBSERVE_ONLY,
            "self_evolve_enabled": config.SELF_EVOLVE_ENABLED,
            "human_approval_required": config.HUMAN_APPROVAL_REQUIRED,
        },
    }


@app.post("/research/brief", response_model=BriefResult, dependencies=[Depends(require_key)])
async def research_brief(req: ResearchBriefRequest) -> BriefResult:
    """Ad-hoc brief for a single topic (relevance-ranked)."""
    return await sweep.run_topic(req.topic, req.max_sources, req.categories)


@app.post("/research/run-now", response_model=BriefResult, dependencies=[Depends(require_key)])
async def run_now() -> BriefResult:
    """Trigger the scheduled category sweep immediately."""
    return await sweep.run_sweep()


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=config.PORT, log_level=config.LOG_LEVEL.lower())
