"""Skill discoverability: goal-in, ranked-skills-out search over this repo's
local `.claude/skills/*/SKILL.md` catalog. Reuses the existing free-tier
OpenRouter call (`app.core.model_routes.openrouter_chat`) to rank matches,
falling back to a plain substring matcher whenever the LLM is unavailable
or misbehaves — this endpoint never returns a 5xx for an LLM-availability
problem, only for a genuinely malformed request.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Optional

import yaml
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.core.model_routes import openrouter_chat

logger = logging.getLogger(__name__)

router = APIRouter()

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
_WORD_RE = re.compile(r"[a-z0-9]+")

# backend/app/api/v1/endpoints/skills.py -> parents[5] is the repo root
_REPO_ROOT_FALLBACK = Path(__file__).resolve().parents[5] / ".claude" / "skills"


class SkillSearchRequest(BaseModel):
    goal: str


class SkillMatch(BaseModel):
    name: str
    rationale: str


class SkillSearchResponse(BaseModel):
    matches: list[SkillMatch]
    usedFallback: bool
    error: Optional[str] = None


def _parse_skill_md(path: Path) -> Optional[dict]:
    """Parse one SKILL.md's YAML frontmatter into {"name", "description"};
    returns None (and logs) for anything unusable rather than raising."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        logger.warning("Could not read %s: %s", path, exc)
        return None

    match = _FRONTMATTER_RE.match(text)
    if not match:
        logger.warning("No frontmatter block found in %s", path)
        return None

    try:
        data = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        logger.warning("Malformed YAML frontmatter in %s: %s", path, exc)
        return None

    if not isinstance(data, dict):
        logger.warning("Frontmatter in %s is not a mapping", path)
        return None

    name = data.get("name")
    description = data.get("description")
    if not isinstance(name, str) or not isinstance(description, str):
        logger.warning("Missing name/description in %s", path)
        return None

    return {"name": name, "description": description}


def _load_catalog_from(root: Path) -> list[dict]:
    """Parse every SKILL.md under root/*/SKILL.md into {"name","description"} dicts."""
    if not root.is_dir():
        return []

    catalog = []
    for skill_md in sorted(root.glob("*/SKILL.md")):
        parsed = _parse_skill_md(skill_md)
        if parsed is not None:
            catalog.append(parsed)
    return catalog


def _load_catalog() -> list[dict]:
    """Load the skill catalog from the mounted container path, falling back to
    a repo-root-relative path when that mount doesn't exist (local dev/tests)."""
    configured = Path(settings.SKILLS_CATALOG_PATH)
    if configured.is_dir():
        return _load_catalog_from(configured)
    return _load_catalog_from(_REPO_ROOT_FALLBACK)


def _fallback_match(goal: str, catalog: list[dict], limit: int = 5) -> list[dict]:
    """Case-insensitive substring match against name+description. Never empty
    when the catalog itself is non-empty — falls back to the first `limit`
    entries if nothing scores above zero."""
    words = [w for w in _WORD_RE.findall(goal.lower()) if len(w) >= 3]

    scored = []
    for entry in catalog:
        haystack = f"{entry['name']} {entry['description']}".lower()
        score = sum(1 for w in words if w in haystack)
        scored.append((score, entry))

    scored.sort(key=lambda pair: pair[0], reverse=True)

    if not scored or scored[0][0] == 0:
        return [
            {"name": e["name"], "rationale": "No strong keyword match; showing available skills."}
            for e in catalog[:limit]
        ]

    return [
        {
            "name": e["name"],
            "rationale": f'Matched keywords in "{goal}" against this skill\'s name/description.',
        }
        for score, e in scored[:limit]
        if score > 0
    ]


def _build_system_prompt(catalog: list[dict]) -> str:
    catalog_block = "\n".join(f"{e['name']}: {e['description']}" for e in catalog)
    return (
        "You are a skill-matching assistant for a developer tool. Here is the "
        "full catalog of available skills, one per line as \"name: description\":\n\n"
        f"{catalog_block}\n\n"
        "Given the user's goal, select the top 3-5 most relevant skills from the "
        "list above. Respond with ONLY valid JSON, no markdown fences, no prose, "
        'in exactly this shape: {"matches":[{"name":"<exact skill name from the '
        'list>","rationale":"<one sentence>"}]}. Do not invent skill names not '
        "in the list."
    )


def _parse_llm_response(raw: str, catalog: list[dict]) -> list[dict]:
    """Parse and validate the LLM's JSON reply. Raises ValueError (including
    its json.JSONDecodeError subclass) on any problem — malformed JSON,
    wrong shape, or every returned name being a hallucination."""
    data = json.loads(raw)
    if not isinstance(data, dict) or not isinstance(data.get("matches"), list):
        raise ValueError("response missing a 'matches' list")

    valid_names = {e["name"] for e in catalog}
    matches = []
    seen_names: set[str] = set()
    for item in data["matches"]:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        rationale = item.get("rationale")
        if name in valid_names and isinstance(rationale, str) and name not in seen_names:
            matches.append({"name": name, "rationale": rationale})
            seen_names.add(name)

    if not matches:
        raise ValueError("no valid matches after filtering hallucinated names")

    return matches


@router.post("/search", response_model=SkillSearchResponse)
async def search_skills(body: SkillSearchRequest) -> SkillSearchResponse:
    """POST /api/v1/skills/search — goal-in, ranked-skills-out.

    Always returns HTTP 200 (fail-soft) except for a malformed request body
    (missing `goal`, handled by FastAPI/Pydantic's automatic 422).

    Deliberately no auth/rate-limit dependency, same tier as this repo's
    other read-only dashboard-facing endpoints (health, fleet, agents-status)
    — see docs/superpowers/specs/2026-09-12-skill-discoverability-design.md
    §9. A `slowapi` `@limiter.limit(...)` decorator was tried and reverted:
    it broke FastAPI's body-model binding for `body` (silently rebound it as
    a query parameter, 422 on every real call) with this repo's installed
    slowapi/FastAPI versions, and no other endpoint in this codebase
    actually uses that decorator today. Revisit only alongside a real
    slowapi integration test, not as a one-off addition here.
    """
    catalog = _load_catalog()

    if not catalog:
        return SkillSearchResponse(
            matches=[], usedFallback=True, error="skill catalog is empty or unreadable"
        )

    if not settings.OPENROUTER_API_KEY:
        fallback = _fallback_match(body.goal, catalog)
        return SkillSearchResponse(
            matches=fallback, usedFallback=True, error="OPENROUTER_API_KEY not configured"
        )

    try:
        raw = await openrouter_chat(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
            model=settings.OPENROUTER_DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": _build_system_prompt(catalog)},
                {"role": "user", "content": body.goal},
            ],
            max_tokens=500,
            # goal is free-text user input, unlike the internally-authored
            # system prompt — redact anything that looks like a credential
            # before it leaves the process, same tool Brain.think() uses.
            privacy_mode="redact",
            # keep this comfortably inside the dashboard proxy's own 15s
            # timeout so a slow call resolves to OUR fallback, not an
            # abandoned request racing the proxy's independent timeout.
            timeout_seconds=12.0,
        )
        matches = _parse_llm_response(raw, catalog)
        return SkillSearchResponse(matches=matches, usedFallback=False, error=None)
    except Exception as exc:
        # Broad on purpose: openrouter_chat can raise RuntimeError (bad
        # response shape), CircuitBreakerOpen, or an unwrapped httpx
        # network/timeout error (ConnectError, TimeoutException, ...) —
        # Brain.think() catches the same call the same way for the same
        # reason. Anything here means "the LLM path didn't work", and the
        # substring fallback below is what makes this endpoint fail-soft.
        logger.warning("Skill search falling back to substring match: %s", exc)
        fallback = _fallback_match(body.goal, catalog)
        return SkillSearchResponse(
            matches=fallback,
            usedFallback=True,
            error="LLM ranking unavailable, showing substring matches",
        )
