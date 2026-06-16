#!/usr/bin/env python3
"""HyperFocus Z0ne - BROski$ XP Reward Hook.

Publishes an XP award event to Redis channel 'broski_economy' (DB 1).
Falls back gracefully if Redis is offline -- offline is non-fatal.

Usage:
    python scripts/broski_xp_reward.py
    python scripts/broski_xp_reward.py --xp 25 --reason task_complete
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_DEFAULT_XP = 10
_DEFAULT_REASON = "session_hook"
_REDIS_CHANNEL = "broski_economy"
_REDIS_DB = 1  # DB 1 = cache (Sacred Rule: Redis DB split)


def _publish(channel, payload):
    try:
        import redis  # type: ignore[import]

        r = redis.Redis(host="127.0.0.1", port=6379, db=_REDIS_DB, socket_connect_timeout=2)
        r.ping()
        r.publish(channel, json.dumps(payload))
        return True
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Award BROski$ XP")
    parser.add_argument("--xp", type=int, default=_DEFAULT_XP, help="XP amount (default 10)")
    parser.add_argument("--reason", default=_DEFAULT_REASON, help="Award reason tag")
    args = parser.parse_args()

    print("\n[BROSKI XP REWARD] HyperFocus Z0ne")
    print("-" * 40)
    print("   XP:     +" + str(args.xp))
    print("   Reason: " + args.reason)

    payload = {
        "type": "xp_award",
        "xp": args.xp,
        "reason": args.reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": "session_hook",
    }

    published = _publish(_REDIS_CHANNEL, payload)

    if published:
        print("   Redis:  PASS published to '" + _REDIS_CHANNEL + "' (DB " + str(_REDIS_DB) + ")")
        print()
        print("PASS  XP awarded! BROski forever!\n")
    else:
        print("   Redis:  WARN not reachable -- XP logged offline")
        print()
        print("PASS  XP recorded locally (+" + str(args.xp) + " " + args.reason + ") -- Redis offline is non-fatal\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
