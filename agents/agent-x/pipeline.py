"""
Agent X — Evolutionary Pipeline
=================================
The self-upgrade engine. Detects degraded agents, generates improvements,
builds new images, deploys safely, and rolls back on failure.

Cycle stages:
  1. SCAN    — poll all agents for health + performance metrics
  2. SCORE   — grade each agent (0-100) based on health/error rate/uptime
  3. FLAG    — identify agents below threshold
  4. DESIGN  — ask LLM to suggest improvements for flagged agents
  5. BUILD   — build new Docker image with improved code (dry-run by default)
  6. DEPLOY  — blue-green deploy with health verification
  7. VERIFY  — confirm new version is healthy
  8. COMMIT  — record result; rollback if unhealthy

Safety: dry_run=True (default) generates the plan without executing steps 5-7.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import httpx

from agentx.docker_ops import (
    build_image,
    container_health,
    deploy_service,
    get_container_image,
    wait_for_healthy,
    WORKSPACE,
    COMPOSE_FILE,
)
from agentx.designer import suggest_improvement

logger = logging.getLogger(__name__)

HEALTH_SCORE_THRESHOLD = int(os.getenv("AGENT_HEALTH_THRESHOLD", "60"))
OBSERVER_URL = os.getenv("OBSERVER_URL", "http://hyper-observer:8092")


# ── Data classes ──────────────────────────────────────────────────────────────

class PipelineStage(str, Enum):
    IDLE = "idle"
    SCANNING = "scanning"
    SCORING = "scoring"
    DESIGNING = "designing"
    BUILDING = "building"
    DEPLOYING = "deploying"
    VERIFYING = "verifying"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class AgentScore:
    name: str
    container_name: str
    health_endpoint: str
    score: int          # 0-100
    healthy: bool
    reachable: bool
    issues: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def needs_attention(self) -> bool:
        return self.score < HEALTH_SCORE_THRESHOLD or not self.reachable


@dataclass
class EvolutionRecord:
    cycle_id: str
    started_at: float
    completed_at: Optional[float] = None
    stage: PipelineStage = PipelineStage.IDLE
    dry_run: bool = True
    agents_scanned: int = 0
    agents_flagged: list[str] = field(default_factory=list)
    improvements_designed: list[dict[str, Any]] = field(default_factory=list)
    builds_attempted: list[str] = field(default_factory=list)
    builds_succeeded: list[str] = field(default_factory=list)
    deploys_succeeded: list[str] = field(default_factory=list)
    rollbacks_triggered: list[str] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def duration_seconds(self) -> float:
        end = self.completed_at or time.time()
        return round(end - self.started_at, 2)

    def summary(self) -> dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "stage": self.stage.value,
            "dry_run": self.dry_run,
            "duration_seconds": self.duration_seconds,
            "agents_scanned": self.agents_scanned,
            "agents_flagged": self.agents_flagged,
            "improvements_designed": len(self.improvements_designed),
            "builds_succeeded": self.builds_succeeded,
            "deploys_succeeded": self.deploys_succeeded,
            "rollbacks_triggered": self.rollbacks_triggered,
            "error": self.error,
        }


# ── Known agents manifest ─────────────────────────────────────────────────────
# The pipeline knows about all hyper-agents and can be extended.

KNOWN_AGENTS: list[dict[str, Any]] = [
    {
        "name": "hyper-architect",
        "container_name": "hyper-architect",
        "health_url": "http://hyper-architect:8091/health",
        "stats_url": "http://hyper-architect:8091/stats",
        "dockerfile": "agents/hyper-agents/architect/Dockerfile",
        "code_path": "agents/hyper-agents/architect/main.py",
        "service_name": "hyper-architect",
    },
    {
        "name": "hyper-observer",
        "container_name": "hyper-observer",
        "health_url": "http://hyper-observer:8092/health",
        "stats_url": "http://hyper-observer:8092/stats",
        "dockerfile": "agents/hyper-agents/observer/Dockerfile",
        "code_path": "agents/hyper-agents/observer/main.py",
        "service_name": "hyper-observer",
    },
    {
        "name": "hyper-worker",
        "container_name": "hyper-worker",
        "health_url": "http://hyper-worker:8093/health",
        "stats_url": "http://hyper-worker:8093/stats",
        "dockerfile": "agents/hyper-agents/worker/Dockerfile",
        "code_path": "agents/hyper-agents/worker/main.py",
        "service_name": "hyper-worker",
    },
]


# ── Stage implementations ─────────────────────────────────────────────────────

async def _fetch_agent_data(
    client: httpx.AsyncClient,
    health_url: str,
    stats_url: str,
) -> tuple[bool, dict[str, Any], dict[str, Any]]:
    """Fetch health + stats for an agent. Returns (reachable, health, stats)."""
    try:
        h_resp = await client.get(health_url, timeout=5.0)
        health = h_resp.json() if h_resp.status_code == 200 else {}
    except Exception:
        return False, {}, {}

    try:
        s_resp = await client.get(stats_url, timeout=5.0)
        stats = s_resp.json() if s_resp.status_code == 200 else {}
    except Exception:
        stats = {}

    return True, health, stats


def _score_agent(
    name: str,
    reachable: bool,
    health: dict[str, Any],
    stats: dict[str, Any],
) -> AgentScore:
    """Score an agent 0-100 based on health signals."""
    if not reachable:
        return AgentScore(
            name=name,
            container_name=name,
            health_endpoint="",
            score=0,
            healthy=False,
            reachable=False,
            issues=["Agent unreachable — container may be down"],
        )

    score = 100
    issues = []

    # Health status check
    status = health.get("status", "unknown")
    if status == "error":
        score -= 40
        issues.append(f"Agent in ERROR state")
    elif status == "starting":
        score -= 20
        issues.append("Agent still starting")

    # Worker-specific: success rate
    success_rate_str = stats.get("success_rate", "100.0%")
    try:
        success_rate = float(success_rate_str.strip("%"))
        if success_rate < 50:
            score -= 30
            issues.append(f"Low success rate: {success_rate_str}")
        elif success_rate < 80:
            score -= 15
            issues.append(f"Below-average success rate: {success_rate_str}")
    except (ValueError, AttributeError):
        pass

    # Observer-specific: active alerts
    active_alerts = stats.get("active_alerts", 0)
    if active_alerts > 0:
        score -= min(active_alerts * 5, 25)
        issues.append(f"{active_alerts} active alert(s)")

    score = max(0, score)
    return AgentScore(
        name=name,
        container_name=name,
        health_endpoint="",
        score=score,
        healthy=status not in ("error",),
        reachable=True,
        issues=issues,
        stats=stats,
    )


# ── Pipeline orchestrator ─────────────────────────────────────────────────────

class EvolutionaryPipeline:
    """Orchestrates the full detect → design → build → deploy cycle."""

    def __init__(self) -> None:
        self._history: list[EvolutionRecord] = []
        self._current: Optional[EvolutionRecord] = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def history(self) -> list[EvolutionRecord]:
        return self._history

    @property
    def last_cycle(self) -> Optional[EvolutionRecord]:
        return self._history[-1] if self._history else None

    async def scan(self) -> list[AgentScore]:
        """Stage 1+2: Scan all known agents and return scored results."""
        scores: list[AgentScore] = []
        async with httpx.AsyncClient() as client:
            for manifest in KNOWN_AGENTS:
                reachable, health, stats = await _fetch_agent_data(
                    client,
                    manifest["health_url"],
                    manifest["stats_url"],
                )
                score = _score_agent(manifest["name"], reachable, health, stats)
                scores.append(score)
        return scores

    async def run_cycle(self, dry_run: bool = True) -> EvolutionRecord:
        """Run a full evolutionary pipeline cycle.

        Args:
            dry_run: If True, generate plan only — no Docker builds or deploys.

        Returns:
            EvolutionRecord with full cycle results.
        """
        if self._running:
            raise RuntimeError("Pipeline already running. Wait for current cycle to complete.")

        import uuid
        cycle_id = str(uuid.uuid4())[:8]
        record = EvolutionRecord(
            cycle_id=cycle_id,
            started_at=time.time(),
            dry_run=dry_run,
        )
        self._current = record
        self._running = True

        try:
            # ── Stage 1+2: Scan + Score ───────────────────────────────────
            record.stage = PipelineStage.SCANNING
            logger.info(f"[Pipeline:{cycle_id}] Scanning {len(KNOWN_AGENTS)} agents...")
            scores = await self.scan()
            record.agents_scanned = len(scores)

            flagged = [s for s in scores if s.needs_attention]
            record.agents_flagged = [s.name for s in flagged]
            record.stage = PipelineStage.SCORING

            if not flagged:
                logger.info(f"[Pipeline:{cycle_id}] All agents healthy — no action needed.")
                record.stage = PipelineStage.COMPLETE
                record.completed_at = time.time()
                self._history.append(record)
                return record

            logger.info(
                f"[Pipeline:{cycle_id}] {len(flagged)} agent(s) flagged: "
                f"{record.agents_flagged}"
            )

            # ── Stage 3: Design improvements ──────────────────────────────
            record.stage = PipelineStage.DESIGNING
            for agent_score in flagged:
                manifest = next(
                    (m for m in KNOWN_AGENTS if m["name"] == agent_score.name),
                    None,
                )
                if not manifest:
                    continue

                code_path = os.path.join(WORKSPACE, manifest["code_path"])
                try:
                    with open(code_path, encoding="utf-8") as f:
                        current_code = f.read()
                except OSError:
                    current_code = "# Code not accessible"

                improvement = await suggest_improvement(
                    agent_name=agent_score.name,
                    current_code=current_code,
                    performance_data={
                        "score": agent_score.score,
                        "issues": agent_score.issues,
                        "stats": agent_score.stats,
                    },
                )
                improvement["agent"] = agent_score.name
                improvement["score"] = agent_score.score
                record.improvements_designed.append(improvement)
                logger.info(
                    f"[Pipeline:{cycle_id}] Improvement for {agent_score.name}: "
                    f"{improvement.get('issue', 'N/A')}"
                )

            if dry_run:
                logger.info(f"[Pipeline:{cycle_id}] DRY RUN — stopping before build/deploy.")
                record.stage = PipelineStage.COMPLETE
                record.completed_at = time.time()
                self._history.append(record)
                return record

            # ── Stage 4: Build new images ──────────────────────────────────
            record.stage = PipelineStage.BUILDING
            for agent_score in flagged:
                manifest = next(
                    (m for m in KNOWN_AGENTS if m["name"] == agent_score.name),
                    None,
                )
                if not manifest:
                    continue

                version = f"evolved-{cycle_id}"
                record.builds_attempted.append(agent_score.name)

                build_result = await build_image(
                    name=agent_score.name,
                    version=version,
                    dockerfile_path=os.path.join(WORKSPACE, manifest["dockerfile"]),
                    context_path=WORKSPACE,
                )
                if build_result.success:
                    record.builds_succeeded.append(agent_score.name)
                    logger.info(f"[Pipeline:{cycle_id}] Built {build_result.image_tag}")
                else:
                    logger.error(
                        f"[Pipeline:{cycle_id}] Build FAILED for {agent_score.name}: "
                        f"{build_result.error}"
                    )

            # ── Stage 5: Deploy ────────────────────────────────────────────
            record.stage = PipelineStage.DEPLOYING
            for agent_name in record.builds_succeeded:
                manifest = next(
                    (m for m in KNOWN_AGENTS if m["name"] == agent_name), None
                )
                if not manifest:
                    continue

                old_image = await get_container_image(manifest["container_name"])

                deploy_result = await deploy_service(
                    service_name=manifest["service_name"],
                    compose_file=COMPOSE_FILE,
                    build=False,
                )

                # ── Stage 6: Verify ────────────────────────────────────────
                record.stage = PipelineStage.VERIFYING
                healthy = await wait_for_healthy(
                    manifest["container_name"],
                    timeout_seconds=90,
                )

                if healthy:
                    record.deploys_succeeded.append(agent_name)
                    logger.info(f"[Pipeline:{cycle_id}] Deployed + verified {agent_name}")
                else:
                    logger.warning(
                        f"[Pipeline:{cycle_id}] {agent_name} unhealthy after deploy — rolling back"
                    )
                    record.rollbacks_triggered.append(agent_name)
                    if old_image:
                        from agentx.docker_ops import rollback_to_image
                        await rollback_to_image(manifest["container_name"], old_image)

            record.stage = PipelineStage.COMPLETE
            record.completed_at = time.time()

        except Exception as exc:
            logger.error(f"[Pipeline:{cycle_id}] Unhandled error: {exc}", exc_info=True)
            record.stage = PipelineStage.FAILED
            record.error = str(exc)
            record.completed_at = time.time()

        finally:
            self._running = False
            self._history.append(record)
            self._current = record

        return record

    def current_status(self) -> dict[str, Any]:
        if self._current and self._running:
            return {"running": True, "cycle": self._current.summary()}
        if self._history:
            return {"running": False, "last_cycle": self._history[-1].summary()}
        return {"running": False, "last_cycle": None}
