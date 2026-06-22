#!/usr/bin/env python3
"""HyperFocus Z0ne - Session Start Hook (thin wrapper -> _broski_hook_core).

Writes a .focus_session_start marker, checks .env + core compose, pings Redis.
Behaviour lives in _broski_hook_core.run_session_start; config in hooks_config.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _broski_hook_core as core  # noqa: E402
import hooks_config as cfg  # noqa: E402

if __name__ == "__main__":
    sys.exit(core.run_session_start(
        label=cfg.LABEL,
        compose_files=cfg.COMPOSE_FILES,
        fail_if_missing_compose=cfg.SESSION_FAIL_IF_MISSING_COMPOSE,
    ))
