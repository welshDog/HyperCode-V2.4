"""Safety Shepherd — pure runtime policy engine (P0-2).

Evaluates a proposed agent action against a capabilities manifest and returns a
decision: ALLOW | BLOCK | ESCALATE. This module is dependency-free and fully
deterministic so it can be unit-tested without FastAPI, Redis, or Docker.

Decision precedence (first match wins):
  1. exempt category (e.g. stripe)            -> ALLOW   (sacred rule: never gate Stripe)
  2. hard-blocked target (secrets/.env/...)   -> BLOCK
  3. unknown agent (no caps, no wildcard)     -> ESCALATE
  4. blocked domain                           -> BLOCK
  5. file_write outside allowed paths         -> BLOCK
  6. action-rate over the agent's max_actions -> ESCALATE
  7. tool not in the agent's allowlist        -> ESCALATE
  8. http_external to a non-allowlisted domain-> ESCALATE
  9. dangerous category without explicit grant-> ESCALATE
 10. otherwise                                -> ALLOW
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from typing import Any, Optional

ALLOW = "ALLOW"
BLOCK = "BLOCK"
ESCALATE = "ESCALATE"

# Categories that are inherently risky and require an explicit capability grant.
DANGEROUS = {"docker", "http_external", "file_write", "stripe", "discord"}


@dataclass
class Decision:
    decision: str
    reason: str
    rule: str
    category: Optional[str] = None
    agent: Optional[str] = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "reason": self.reason,
            "rule": self.rule,
            "category": self.category,
            "agent": self.agent,
        }


def _match_any(value: str, patterns: list[str]) -> bool:
    """Glob match supporting ** as 'any path segments'."""
    if not value:
        return False
    norm = value.replace("\\", "/")
    for pat in patterns or []:
        p = pat.replace("\\", "/").replace("**", "*")
        if fnmatch.fnmatch(norm, p) or fnmatch.fnmatch(norm, f"*/{p}"):
            return True
    return False


def _agent_caps(manifest: dict[str, Any], agent: str) -> Optional[dict[str, Any]]:
    agents = manifest.get("agents", {}) or {}
    if agent in agents:
        return agents[agent]
    return agents.get("*")


def evaluate(
    manifest: dict[str, Any],
    request: dict[str, Any],
    action_count: int = 0,
) -> Decision:
    """Evaluate a proposed action.

    request keys:
      agent     — requesting agent name
      category  — one of DANGEROUS, or a generic category (default "generic")
      tool      — the specific tool/operation name (optional)
      target    — file path for file_*; resource id otherwise (optional)
      domain    — host for http_external / discord / stripe (optional)
    action_count — actions already taken by this agent in the current window.
    """
    agent = str(request.get("agent") or "").strip()
    category = str(request.get("category") or "generic").strip().lower()
    tool = request.get("tool")
    target = str(request.get("target") or "")
    domain = str(request.get("domain") or "")

    defaults = manifest.get("defaults", {}) or {}
    exempt = set(manifest.get("exempt_categories", []) or [])
    blocked_paths = manifest.get("blocked_paths", []) or []
    blocked_domains = set(manifest.get("blocked_domains", []) or [])

    # 1. Exempt categories are always allowed (Stripe must never be gated).
    if category in exempt:
        return Decision(ALLOW, f"category '{category}' is exempt", "exempt", category, agent)

    # 2. Hard-blocked targets — secrets/.env never writable regardless of agent.
    if target and _match_any(target, blocked_paths):
        return Decision(BLOCK, f"target '{target}' is hard-blocked", "blocked_path", category, agent)

    # 3. Unknown agent (no specific caps and no wildcard default).
    caps = _agent_caps(manifest, agent)
    if caps is None:
        decision = defaults.get("unknown_agent_decision", ESCALATE)
        return Decision(decision, f"no capabilities for agent '{agent}'", "unknown_agent", category, agent)

    allowed_tools = caps.get("tools", []) or []
    allowed_paths = caps.get("file_paths", []) or []
    allowed_domains = caps.get("domains", []) or []
    max_actions = caps.get("max_actions", defaults.get("max_actions", 0)) or 0

    # 4. Blocked domain.
    if domain and domain in blocked_domains:
        return Decision(BLOCK, f"domain '{domain}' is blocked", "blocked_domain", category, agent)

    # 5. file_write outside the agent's allowed paths.
    if category == "file_write" and target and not _match_any(target, allowed_paths):
        return Decision(BLOCK, f"file_write to '{target}' outside allowed paths", "path_not_allowed", category, agent)

    # 6. Action-rate ceiling.
    if max_actions and action_count >= max_actions:
        return Decision(
            ESCALATE,
            f"agent '{agent}' hit action ceiling ({action_count}/{max_actions})",
            "rate_ceiling", category, agent,
        )

    # 7. Tool not in the agent's allowlist.
    if tool and allowed_tools and tool not in allowed_tools:
        return Decision(ESCALATE, f"tool '{tool}' not granted to '{agent}'", "tool_not_granted", category, agent)

    # 8. External HTTP to a non-allowlisted domain.
    if category == "http_external" and domain and domain not in allowed_domains:
        return Decision(ESCALATE, f"external call to '{domain}' not allowlisted", "domain_not_granted", category, agent)

    # 9. Dangerous category without an explicit tool/grant.
    if category in DANGEROUS and category not in allowed_tools and tool not in allowed_tools:
        return Decision(ESCALATE, f"dangerous category '{category}' needs explicit grant", "dangerous_ungranted", category, agent)

    # 10. Default allow.
    return Decision(ALLOW, "action within granted capabilities", "default_allow", category, agent)
