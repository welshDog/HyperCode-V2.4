#!/usr/bin/env python3
"""HyperFocus Z0ne - Session End Hook (thin wrapper -> _broski_hook_core).

Reads the .focus_session_start marker, computes duration, appends to
logs/sessions.jsonl, removes the marker. Behaviour in _broski_hook_core.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _broski_hook_core as core  # noqa: E402
import hooks_config as cfg  # noqa: E402

if __name__ == "__main__":
    sys.exit(core.run_session_end(label=cfg.LABEL))
