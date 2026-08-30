"""Central config for the Meta-Research Architect Hyper Agent (Phase 1).

Every knob is an env var with a safe default so the agent boots with zero
configuration. Nothing here reaches outside the process.
"""

from __future__ import annotations

import os


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, "").strip() or default)
    except ValueError:
        return default


def _list(name: str, default: list[str]) -> list[str]:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return default
    return [item.strip() for item in raw.split(",") if item.strip()]


# --- identity -----------------------------------------------------------------
AGENT_NAME = os.getenv("AGENT_NAME", "meta-research-architect")
VERSION = "0.2.0"
PHASE = "1-observe-only"
PORT = _int("META_RESEARCH_ARCHITECT_PORT", 8095)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# --- optional shared-secret auth (matches the other V2.4 agents) -------------
# When unset, non-health endpoints are open (fine for local dev).
AGENT_API_KEY = (os.getenv("AGENT_API_KEY") or os.getenv("HYPERCODE_API_KEY") or "").strip()

# --- research sweep ---------------------------------------------------------
# How often the scheduled sweep runs. Default: weekly.
UPDATE_INTERVAL_SECONDS = _int("RESEARCH_UPDATE_INTERVAL", 7 * 24 * 3600)
ARXIV_CATEGORIES = _list("RESEARCH_ARXIV_CATEGORIES", ["cs.AI", "cs.LG", "cs.MA", "cs.NE"])
MAX_RESULTS_PER_QUERY = _int("RESEARCH_MAX_RESULTS_PER_QUERY", 25)
TOP_PICKS = _int("RESEARCH_TOP_PICKS", 5)
# Run one sweep shortly after startup so a fresh container is not silent for a week.
RUN_ON_STARTUP = (os.getenv("RESEARCH_RUN_ON_STARTUP", "true").strip().lower() == "true")
STARTUP_DELAY_SECONDS = _int("RESEARCH_STARTUP_DELAY_SECONDS", 30)

# --- sinks (all optional, all no-op when unconfigured) ----------------------
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
REDIS_CHANNEL = os.getenv("RESEARCH_REDIS_CHANNEL", "hypercode_research")
REDIS_LATEST_KEY = os.getenv("RESEARCH_REDIS_LATEST_KEY", "research:latest")
REDIS_SEEN_KEY = os.getenv("RESEARCH_REDIS_SEEN_KEY", "research:seen")

DISCORD_WEBHOOK_URL = (os.getenv("RESEARCH_DISCORD_WEBHOOK_URL") or os.getenv("DISCORD_WEBHOOK_URL") or "").strip()

# When set to a writable directory, each brief is also dropped there as a
# markdown note so the Obsidian brain graph / RAG can pick it up.
VAULT_DIR = (os.getenv("RESEARCH_VAULT_DIR") or "").strip()

# --- hard safety facts (Phase 1) -----------------------------------------
OBSERVE_ONLY = True
SELF_EVOLVE_ENABLED = False
HUMAN_APPROVAL_REQUIRED = True
