"""Agent skill-loadout resolution for the crew-orchestrator.

Reads the HYPER-SILLs agent-loadouts.json + skills-registry.json (mounted into
the container) and resolves an agent's mandatory skills. Two uses:

  * resolve_loadout_skills(agent) -> skills to inject into a plan prompt.
  * boot_check(agent) -> startup gate: log the loadout, and (strict mode) refuse
    boot if any required skill is missing/dead.

Every plan is seeded with the agent's required + optional skills BEFORE the
graph-routed situational skills, so the SACRED SIX / FIVE WARDS are always
applied. Forbidden skills are never resolved (a V2.4 agent can't load another
repo's rules).

Fail-open: missing/unreadable files -> [] (agents run without loadout seeding,
exactly like today; a missing mount never bricks an agent). Kept intentionally
tiny; it mirrors HYPER-SILLs scripts/agent_boot.py, whose loadout validator is
the source of truth for the data.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_DEAD_STATUSES = {"deprecated", "archived"}
_DEFAULT_LOADOUTS = "/skills/agent-loadouts.json"
_DEFAULT_REGISTRY = "/skills/skills-registry.json"


class BootCheckError(RuntimeError):
    """Raised when an agent's required skills are unavailable and strict mode is on."""


def _is_available(skill: Optional[Dict[str, Any]]) -> bool:
    return bool(skill) and skill.get("status", "").lower() not in _DEAD_STATUSES


def _read(
    loadouts_path: Optional[str], registry_path: Optional[str]
) -> Tuple[Optional[dict], Optional[Dict[str, dict]]]:
    """Load (loadouts, registry-by-id), or (None, None) on any failure (fail-open)."""
    lo_path = loadouts_path or os.getenv("AGENT_LOADOUTS_PATH", _DEFAULT_LOADOUTS)
    reg_path = registry_path or os.getenv("SKILLS_REGISTRY_PATH", _DEFAULT_REGISTRY)
    try:
        loadouts = json.loads(Path(lo_path).read_text(encoding="utf-8"))
        registry = {
            s["id"]: s
            for s in json.loads(Path(reg_path).read_text(encoding="utf-8"))["skills"]
        }
        return loadouts, registry
    except Exception as exc:  # missing mount, bad JSON — degrade to no loadout
        logger.warning(json.dumps({"event": "loadout_unavailable", "reason": str(exc)}))
        return None, None


def _effective(loadouts: dict, agent: Optional[str]) -> Tuple[set, set, set]:
    """Return (required, optional, forbidden) = _defaults merged with the agent entry."""
    defaults = loadouts.get("_defaults", {})
    entry = loadouts.get("agents", {}).get(agent, {}) if agent else {}

    def eff(key: str) -> set:
        return set(defaults.get(key, [])) | set(entry.get(key, []))

    return eff("required"), eff("optional"), eff("forbidden")


def resolve_loadout_skills(
    agent: Optional[str],
    loadouts_path: Optional[str] = None,
    registry_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return the agent's mandatory skills (required + optional, minus forbidden,
    active only) as registry dicts. Fail-open -> []. agent=None yields _defaults."""
    loadouts, registry = _read(loadouts_path, registry_path)
    if loadouts is None:
        return []
    required, optional, forbidden = _effective(loadouts, agent)
    out: List[Dict[str, Any]] = []
    for sid in sorted((required | optional) - forbidden):
        skill = registry.get(sid)
        if _is_available(skill):
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


def boot_check(
    agent: Optional[str],
    strict: Optional[bool] = None,
    loadouts_path: Optional[str] = None,
    registry_path: Optional[str] = None,
) -> List[str]:
    """Startup gate. Resolve the agent's loadout, log it, and return the list of
    REQUIRED skill ids that are missing or deprecated/archived.

    strict (default from env LOADOUT_STRICT): if any required skill is missing,
    raise BootCheckError to refuse full boot. Fail-open: when the loadout files
    are absent (no mount) we cannot determine the loadout, so we never raise —
    a misconfigured mount must not brick the agent.
    """
    if strict is None:
        strict = os.getenv("LOADOUT_STRICT", "false").strip().lower() in ("1", "true", "yes", "on")

    loadouts, registry = _read(loadouts_path, registry_path)
    if loadouts is None:  # no mount -> can't determine -> fail-open, never brick
        logger.warning(json.dumps({"event": "boot_check_skipped", "agent": agent}))
        return []

    required, _, _ = _effective(loadouts, agent)
    missing = sorted(sid for sid in required if not _is_available(registry.get(sid)))

    logger.info(json.dumps({
        "event": "boot_check", "agent": agent,
        "required": len(required), "missing": missing,
    }))
    if missing:
        logger.error(json.dumps({
            "event": "boot_check_missing_required", "agent": agent, "missing": missing,
        }))
        if strict:
            raise BootCheckError(
                f"Agent '{agent}' is missing required skills {missing} — refusing full boot. "
                f"Set LOADOUT_STRICT=false to degrade."
            )
    return missing
