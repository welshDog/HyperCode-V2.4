"""Agent skill-loadout resolution for the crew-orchestrator.

Reads the HYPER-SILLs agent-loadouts.json + skills-registry.json (mounted into
the container) and resolves an agent's mandatory skills for prompt injection.
Every plan is seeded with the agent's required + optional skills BEFORE the
graph-routed situational skills, so the SACRED SIX / FIVE WARDS are always
applied. Forbidden skills are never resolved (a V2.4 agent can't load another
repo's rules).

Fail-open: missing/unreadable files -> [] (agents run without loadout seeding,
exactly like today). Kept intentionally tiny; it mirrors HYPER-SILLs
scripts/agent_boot.py resolve_loadout, whose loadout validator is the source of
truth for the data.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DEAD_STATUSES = {"deprecated", "archived"}
_DEFAULT_LOADOUTS = "/skills/agent-loadouts.json"
_DEFAULT_REGISTRY = "/skills/skills-registry.json"


def resolve_loadout_skills(
    agent: Optional[str],
    loadouts_path: Optional[str] = None,
    registry_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return the agent's mandatory skills (required + optional, minus forbidden,
    active only) as registry dicts. Fail-open -> []. agent=None yields _defaults."""
    lo_path = loadouts_path or os.getenv("AGENT_LOADOUTS_PATH", _DEFAULT_LOADOUTS)
    reg_path = registry_path or os.getenv("SKILLS_REGISTRY_PATH", _DEFAULT_REGISTRY)
    try:
        loadouts = json.loads(Path(lo_path).read_text(encoding="utf-8"))
        registry = {
            s["id"]: s
            for s in json.loads(Path(reg_path).read_text(encoding="utf-8"))["skills"]
        }
    except Exception as exc:  # missing mount, bad JSON — degrade to no loadout
        logger.warning(json.dumps({"event": "loadout_unavailable", "reason": str(exc)}))
        return []

    defaults = loadouts.get("_defaults", {})
    entry = loadouts.get("agents", {}).get(agent, {}) if agent else {}

    def effective(key: str) -> set:
        return set(defaults.get(key, [])) | set(entry.get(key, []))

    required = effective("required")
    optional = effective("optional")
    forbidden = effective("forbidden")

    out: List[Dict[str, Any]] = []
    for sid in sorted((required | optional) - forbidden):
        skill = registry.get(sid)
        if skill and skill.get("status", "").lower() not in _DEAD_STATUSES:
            out.append(skill)
    return out


def loadout_block(skills: List[Dict[str, Any]]) -> str:
    """Render the loadout as a prompt block (mandatory skills, applied first)."""
    if not skills:
        return ""
    lines = "\n".join(
        f"- {s.get('emoji') or '🦸'} {s.get('hero_name') or s.get('id')} "
        f"({s.get('id')}): {s.get('description')}"
        for s in skills
    )
    return (
        "\n\n[Loadout — this agent's mandatory HYPER-SILLs skills; "
        "apply these first, before the routed skills below]\n" + lines
    )
