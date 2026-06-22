#!/usr/bin/env python3
"""HyperFocus Z0ne - per-repo hook config for HyperCode-V2.4.

The ~20% that varies per repo. Consumed by the thin hook wrappers, which call
_broski_hook_core.run_*(). Keep this file repo-specific; the core stays shared.
"""

# Empty label = no " -- <repo>" suffix in hook headers (HyperCode is the home repo).
LABEL = ""

# env_guard
ENV_REQUIRED = ["POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "REDIS_URL", "SECRET_KEY"]
ENV_PLACEHOLDERS_EXTRA: list[str] = []
ENV_FILES = [".env"]
ENV_STRIP_QUOTES = False
ENV_MODE = "fail"

# session_start
COMPOSE_FILES = ["docker-compose.core.yml"]
SESSION_FAIL_IF_MISSING_COMPOSE = True

# broski_xp_reward
XP_CHANNEL = "broski_economy"
XP_DB = 1
XP_SOURCE = "session_hook"  # repo attribution in the XP payload
