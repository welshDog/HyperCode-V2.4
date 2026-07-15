#!/usr/bin/env python3
"""HyperFocus Z0ne - BROski$ XP Reward Hook (thin wrapper -> _broski_hook_core).

Publishes an XP award to Redis channel 'broski_economy' (DB 1), TCP with a
docker-exec fallback. Offline is non-fatal. Logic in _broski_hook_core.

Usage:
    python scripts/broski_xp_reward.py
    python scripts/broski_xp_reward.py --xp 25 --reason task_complete
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _broski_hook_core as core  # noqa: E402
import hooks_config as cfg  # noqa: E402

if __name__ == "__main__":
    sys.exit(core.run_xp_reward(
        label=cfg.LABEL,
        argv=sys.argv[1:],
        channel=cfg.XP_CHANNEL,
        db=cfg.XP_DB,
        source=cfg.XP_SOURCE,
    ))
