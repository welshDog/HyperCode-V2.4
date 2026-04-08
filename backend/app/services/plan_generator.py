"""
plan_generator.py — Multi-stage LLM-driven coding plan generator.

Stage 1: High-level phases + objectives
Stage 2: File-level changes per phase
Stage 3: Follow-up instructions for downstream agents
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.agents.brain import brain
from app.core.agent_memory import get_history, read_handoffs
from app.schemas.planning import (
    CodingPlan,
    FileChange,
    FileChangeType,
    ParsedDocument,
    PlanPhase,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_STAGE1_TEMPLATE = """
You are a senior software architect creating a phased coding plan.

Project context (from memory):
{memory_context}

Extracted requirements:
{requirements_text}

Task: Generate a structured JSON coding plan with 2-5 phases.

Strict rules — you MUST follow all of them:
- Focus on INTENT and RATIONALE for each phase.  No code listings.
- Do NOT include file paths inside phase descriptions.
- Do NOT include timelines, estimates, or deadlines.
- Phases must describe high-level objectives and workflow steps only.
- Each workflow step is one logical action (e.g. "Define the database schema").

Output ONLY valid JSON (no markdown fences, no prose):
{{
  "summary": "<one paragraph executive overview>",
  "phases": [
    {{
      "phase_number": 1,
      "title": "<phase title>",
      "description": "<high-level objective — what and why, not how>",
      "workflow_steps": ["<step 1>", "<step 2>"]
    }}
  ]
}}
"""

_STAGE2_TEMPLATE = """
You are a senior software architect identifying file-level changes for a coding plan.

Plan summary: {summary}

Phases:
{phases_text}

Task: For each phase, identify which files must be created, modified, or deleted.

Strict rules:
- Output ONLY file-level changes — no code listings.
- Every entry must include a clear rationale tied to the plan's objectives.
- change_type must be one of: create | modify | delete

Output ONLY valid JSON (no markdown fences):
{{
  "file_changes": [
    {{
      "file_path": "<relative path from repo root>",
      "change_type": "create",
      "description": "<one sentence: what changes>",
      "rationale": "<why this change is needed>"
    }}
  ]
}}
"""

_STAGE3_TEMPLATE = """
You are an AI orchestration specialist writing handoff instructions for downstream coding agents.

Plan summary: {summary}

Phases:
{phases_text}

File changes:
{file_changes_text}

Task: Write concise follow-up instructions for the agents that will execute this plan.
Focus on:
- Ordering dependencies between phases
- Key decisions the executing agent must make
- Integration points that require coordination between agents
- Testing strategy at a high level

Do NOT include code.  Write in plain English, bullet-point format.
Output plain text (not JSON).
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _requirements_to_text(parsed_doc: ParsedDocument) -> str:
    lines = []
    for i, req in enumerate(parsed_doc.requirements, 1):
        lines.append(f"{i}. {req.title}: {req.description}")
        if req.acceptance_criteria:
            lines.append("   Acceptance: " + "; ".join(req.acceptance_criteria))
        if req.technical_constraints:
            lines.append("   Constraints: " + "; ".join(req.technical_constraints))
        if req.dependencies:
            lines.append("   Depends on: " + ", ".join(req.dependencies))
    return "\n".join(lines)


def _phases_to_text(phases: List[PlanPhase]) -> str:
    lines = []
    for p in phases:
        lines.append(f"Phase {p.phase_number} — {p.title}: {p.description}")
        for step in p.workflow_steps:
            lines.append(f"  - {step}")
    return "\n".join(lines)


def _file_changes_to_text(changes: List[FileChange]) -> str:
    return "\n".join(
        f"- [{c.change_type.value.upper()}] {c.file_path}: {c.description}"
        for c in changes
    )


def _build_memory_context(context: Optional[Dict[str, Any]]) -> str:
    """Pull relevant project context from AgentMemory + caller-supplied context dict."""
    parts: List[str] = []

    if context:
        conversation_id = context.get("conversation_id")
        agent_id = context.get("agent_id", "plan_generator")

        if conversation_id:
            try:
                history = get_history(conversation_id, last_n=5)
                if history:
                    history_lines = [
                        f"[{t['agent_id']}|{t['role']}] {t['content']}"
                        for t in history
                    ]
                    parts.append("Recent conversation:\n" + "\n".join(history_lines))
            except Exception as exc:
                logger.warning(f"[PLAN_GENERATOR] Memory context retrieval failed: {exc}")

        try:
            handoffs = read_handoffs(agent_id, limit=3, consume=False)
            if handoffs:
                handoff_lines = [
                    f"- [{h['from_agent_id']}] {h['summary']}" for h in handoffs
                ]
                parts.append("Handoff notes:\n" + "\n".join(handoff_lines))
        except Exception as exc:
            logger.warning(f"[PLAN_GENERATOR] Handoff read failed: {exc}")

        # Include any extra caller-supplied context keys
        for key in ("project_name", "tech_stack", "existing_patterns"):
            if key in context:
                parts.append(f"{key}: {context[key]}")

    return "\n\n".join(parts) if parts else "No additional context available."


# ---------------------------------------------------------------------------
# PlanGenerator
# ---------------------------------------------------------------------------

class PlanGenerator:
    """
    Transforms a ParsedDocument into a structured CodingPlan using
    a 3-stage LLM prompting pipeline via the Brain class.
    """

    async def generate_plan(
        self,
        parsed_doc: ParsedDocument,
        context: Optional[Dict[str, Any]] = None,
    ) -> CodingPlan:
        """
        Main entry point.  Returns a CodingPlan.
        """
        memory_context = _build_memory_context(context)
        requirements_text = _requirements_to_text(parsed_doc)

        # ---- Stage 1: High-level phases ----
        logger.info("[PLAN_GENERATOR] Stage 1: generating phases…")
        stage1_prompt = _STAGE1_TEMPLATE.format(
            memory_context=memory_context,
            requirements_text=requirements_text,
        )
        stage1_raw = await brain.think(
            role="Senior Software Architect",
            task_description=stage1_prompt,
            use_memory=False,
        )
        phases, summary = self._parse_stage1(stage1_raw)

        # ---- Stage 2: File-level changes ----
        logger.info("[PLAN_GENERATOR] Stage 2: identifying file changes…")
        phases_text = _phases_to_text(phases)
        stage2_prompt = _STAGE2_TEMPLATE.format(
            summary=summary,
            phases_text=phases_text,
        )
        stage2_raw = await brain.think(
            role="Senior Software Architect",
            task_description=stage2_prompt,
            use_memory=False,
        )
        file_changes = self._parse_stage2(stage2_raw)

        # ---- Stage 3: Follow-up instructions ----
        logger.info("[PLAN_GENERATOR] Stage 3: compiling follow-up instructions…")
        file_changes_text = _file_changes_to_text(file_changes)
        stage3_prompt = _STAGE3_TEMPLATE.format(
            summary=summary,
            phases_text=phases_text,
            file_changes_text=file_changes_text,
        )
        follow_up = await brain.think(
            role="AI Orchestration Specialist",
            task_description=stage3_prompt,
            use_memory=False,
        )

        return CodingPlan(
            summary=summary,
            phases=phases,
            file_changes_summary=file_changes,
            follow_up_instructions=follow_up.strip() or None,
        )

    # ------------------------------------------------------------------
    # Internal parsers
    # ------------------------------------------------------------------

    def _parse_stage1(self, raw: str) -> tuple[List[PlanPhase], str]:
        """Parse Stage 1 JSON → (phases, summary)."""
        try:
            cleaned = self._strip_fences(raw)
            data = json.loads(cleaned)
            summary = data.get("summary", "No summary provided.")
            phases = []
            for p in data.get("phases", []):
                phases.append(
                    PlanPhase(
                        phase_number=p.get("phase_number", len(phases) + 1),
                        title=p.get("title", "Untitled Phase"),
                        description=p.get("description", ""),
                        workflow_steps=p.get("workflow_steps", []),
                    )
                )
            logger.info(f"[PLAN_GENERATOR] Stage 1 parsed {len(phases)} phase(s).")
            return phases, summary
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning(f"[PLAN_GENERATOR] Stage 1 parse error: {exc}")
            return [
                PlanPhase(
                    phase_number=1,
                    title="Implementation",
                    description=raw[:500],
                    workflow_steps=[],
                )
            ], "Plan generated from document."

    def _parse_stage2(self, raw: str) -> List[FileChange]:
        """Parse Stage 2 JSON → file changes list."""
        try:
            cleaned = self._strip_fences(raw)
            data = json.loads(cleaned)
            changes = []
            for fc in data.get("file_changes", []):
                try:
                    change_type = FileChangeType(fc.get("change_type", "modify"))
                except ValueError:
                    change_type = FileChangeType.MODIFY
                changes.append(
                    FileChange(
                        file_path=fc.get("file_path", "unknown"),
                        change_type=change_type,
                        description=fc.get("description", ""),
                        rationale=fc.get("rationale", ""),
                    )
                )
            logger.info(f"[PLAN_GENERATOR] Stage 2 parsed {len(changes)} file change(s).")
            return changes
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning(f"[PLAN_GENERATOR] Stage 2 parse error: {exc}")
            return []

    @staticmethod
    def _strip_fences(text: str) -> str:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(
                line for line in lines if not line.startswith("```")
            ).strip()
        return cleaned


# Global instance
plan_generator = PlanGenerator()
