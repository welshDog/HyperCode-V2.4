"""
plan_formatter.py — Renders a CodingPlan as Markdown or JSON.

Output order (both formats):
  1. Executive summary
  2. Phased overview  (objectives + workflow steps; no file paths)
  3. File-level changes section
  4. Follow-up instructions (if present)
"""
from __future__ import annotations

from app.schemas.planning import CodingPlan


def format_plan_markdown(plan: CodingPlan) -> str:
    """
    Render a CodingPlan to a human-readable Markdown string.
    Follows: summary → phases → file changes → follow-up instructions.
    """
    lines: list[str] = []

    # ---- 1. Executive Summary ----
    lines.append("# 🗺️ Coding Plan")
    lines.append("")
    lines.append("## Summary")
    lines.append(plan.summary)
    lines.append("")

    # ---- 2. Phased Overview ----
    lines.append("## Phases")
    lines.append("")
    for phase in plan.phases:
        lines.append(f"### Phase {phase.phase_number}: {phase.title}")
        lines.append("")
        lines.append(phase.description)
        lines.append("")
        if phase.workflow_steps:
            for step in phase.workflow_steps:
                lines.append(f"- {step}")
            lines.append("")

    # ---- 3. File-Level Changes ----
    if plan.file_changes_summary:
        lines.append("## File Changes")
        lines.append("")
        lines.append("| File | Change | Description |")
        lines.append("|------|--------|-------------|")
        for fc in plan.file_changes_summary:
            badge = {
                "create": "🟢 create",
                "modify": "🟡 modify",
                "delete": "🔴 delete",
            }.get(fc.change_type.value, fc.change_type.value)
            # Escape pipe characters inside cells
            desc = fc.description.replace("|", "\\|")
            lines.append(f"| `{fc.file_path}` | {badge} | {desc} |")
        lines.append("")

        # Rationale sub-section
        lines.append("### Rationale")
        lines.append("")
        for fc in plan.file_changes_summary:
            lines.append(f"**`{fc.file_path}`** — {fc.rationale}")
            lines.append("")

    # ---- 4. Follow-up Instructions ----
    if plan.follow_up_instructions:
        lines.append("## Follow-up Instructions")
        lines.append("")
        lines.append(plan.follow_up_instructions)
        lines.append("")

    return "\n".join(lines)


def format_plan_json(plan: CodingPlan) -> dict:
    """
    Return the CodingPlan as a structured dict suitable for API responses.
    Field order follows: summary → phases → file_changes_summary → follow_up_instructions.
    """
    return {
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
    }
