#!/usr/bin/env python3
"""HyperFocus Z0ne - Compose Validator (thin wrapper -> _broski_hook_core).

Enforces Sacred Rules on a docker-compose file (no docker.io, no
'from backend.app.', warn on 127.0.0.1 healthchecks). Logic in _broski_hook_core.

Usage:
    python scripts/compose_validator.py docker-compose.core.yml
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _broski_hook_core as core  # noqa: E402
import hooks_config as cfg  # noqa: E402

if __name__ == "__main__":
    sys.exit(core.run_compose_validator(label=cfg.LABEL, argv=sys.argv[1:]))
