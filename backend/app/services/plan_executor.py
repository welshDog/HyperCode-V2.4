"""
plan_executor.py — Converts a CodingPlan into orchestrator workflow steps
and dispatches them via the existing Celery pattern.

Handoff notes are written to Redis at key `memory:handoff:{agent_id}` so
downstream agents have full plan context during execution.
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from app.core.agent_memory import write_handoff
from app.schemas.planning import CodingPlan, PlanPhase

logger = logging.getLogger(__name__)

# File extension → specialist agent routing
_BACKEND_EXTENSIONS = {".py", ".toml", ".cfg", ".ini", ".env", ".sh", ".sql", ".yaml", ".yml"}
_FRONTEND_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx", ".css", ".html", ".vue", ".svelte"}


def _classify_phase(phase: PlanPhase, file_changes_for_phase: list) -> str:
    """
    Determine which specialist agent should handle a given phase.
    Looks at file extensions in the associated file changes.
    Falls back to 'general-specialist'.
    """
    backend_score = 0
    frontend_score = 0

    for fc in file_changes_for_phase:
        path_lower = fc.file_path.lower()
        ext = "." + path_lower.rsplit(".", 1)[-1] if "." in path_lower else ""
        if ext in _BACKEND_EXTENSIONS:
            backend_score += 1
        elif ext in _FRONTEND_EXTENSIONS:
            frontend_score += 1

    if backend_score > frontend_score:
        return "backend-specialist"
    if frontend_score > backend_score:
        return "frontend-specialist"
    # Tie or no file changes → check phase title keywords
    title_lower = phase.title.lower()
    if any(kw in title_lower for kw in ("api", "database", "backend", "server", "model", "schema")):
        return "backend-specialist"
    if any(kw in title_lower for kw in ("ui", "frontend", "component", "style", "page", "view")):
        return "frontend-specialist"
    return "general-specialist"


class PlanExecutor:
    """
    Converts a CodingPlan into Celery workflow steps and dispatches them.
    Also writes Redis handoff notes so executing agents can access full plan context.
    """

    async def submit_plan_to_orchestrator(
        self,
        plan: CodingPlan,
        task_id: Optional[int] = None,
        project_id: Optional[int] = None,
    ) -> dict:
        """
        Submit all plan phases to the Celery queue.
        Returns a summary dict with dispatched job IDs.
        """
        from app.core.celery_app import celery_app  # lazy import to avoid circular deps

        plan_json = json.dumps({
            "summary": plan.summary,
            "phases": [
                {
                    "phase_number": p.phase_number,
                    "title": p.title,
                    "description": p.description,
                    "workflow_steps": p.workflow_steps,
                }
                for p in plan.phases
            ],
            "file_changes_summary": [
                {
                    "file_path": fc.file_path,
                    "change_type": fc.change_type.value,
                    "description": fc.description,
                    "rationale": fc.rationale,
                }
                for fc in plan.file_changes_summary
            ],
            "follow_up_instructions": plan.follow_up_instructions,
        })

        dispatched_jobs = []

        for phase in plan.phases:
            # Collect file changes loosely associated with this phase by index
            # (Stage 2 doesn't tag changes to phases, so we send the full list)
            target_agent = _classify_phase(phase, plan.file_changes_summary)

            # Write handoff note so the executing agent can fetch full plan context
            write_handoff(
                to_agent_id=target_agent,
                from_agent_id="plan_executor",
                summary=(
                    f"[PLAN PHASE {phase.phase_number}] {phase.title}: "
                    f"{phase.description[:300]}"
                ),
                links=[{"type": "plan_json", "content": plan_json}],
            )

            # Build Celery payload
            celery_payload = {
                "id": task_id,
                "title": f"[Phase {phase.phase_number}] {phase.title}",
                "type": target_agent,
                "description": phase.description,
                "priority": "high",
                "status": "pending",
                "project_id": project_id,
                "plan_phase": phase.phase_number,
                "plan_reference": plan_json,
            }

            try:
                celery_app.send_task(
                    "hypercode.tasks.process_agent_job",
                    args=[celery_payload],
                )
                logger.info(
                    f"[PLAN_EXECUTOR] Dispatched Phase {phase.phase_number} "
                    f"→ {target_agent}"
                )
                dispatched_jobs.append({
                    "phase": phase.phase_number,
                    "agent": target_agent,
                    "title": phase.title,
                    "status": "dispatched",
                })
            except Exception as exc:
                logger.error(
                    f"[PLAN_EXECUTOR] Failed to dispatch Phase {phase.phase_number}: {exc}"
                )
                dispatched_jobs.append({
                    "phase": phase.phase_number,
                    "agent": target_agent,
                    "title": phase.title,
                    "status": "error",
                    "error": str(exc),
                })

        return {
            "plan_summary": plan.summary,
            "total_phases": len(plan.phases),
            "dispatched_jobs": dispatched_jobs,
        }


# Global instance
plan_executor = PlanExecutor()
