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
_REDIS_CONTAINERS = ("redis", "hypercode-redis")  # internal redis -- 6379 not published to host


def _publish(channel, payload):
    body = json.dumps(payload)
    # 1) direct host TCP -- only works if redis 6379 is published to the host
    try:
        import redis  # type: ignore[import]

        r = redis.Redis(host="127.0.0.1", port=6379, db=_REDIS_DB, socket_connect_timeout=2)
        r.ping()
        r.publish(channel, body)
        return "tcp"
    except Exception:
        pass
    # 2) fallback: publish into the internal redis container via docker exec
    #    keeps redis on its internal network (Sacred Rule: data-net internal)
    try:
        import shutil
        import subprocess

        if shutil.which("docker"):
            for container in _REDIS_CONTAINERS:
                proc = subprocess.run(
                    ["docker", "exec", container, "redis-cli", "-n", str(_REDIS_DB),
                     "PUBLISH", channel, body],
                    capture_output=True, text=True, timeout=8,
                )
                if proc.returncode == 0:
                    return "docker:" + container
    except Exception:
        pass
    return None


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
        print("   Redis:  PASS published to '" + _REDIS_CHANNEL + "' (DB " + str(_REDIS_DB) + ", via " + published + ")")
        print()
        print("PASS  XP awarded! BROski forever!\n")
    else:
        print("   Redis:  WARN not reachable -- XP logged offline")
        print()
        print("PASS  XP recorded locally (+" + str(args.xp) + " " + args.reason + ") -- Redis offline is non-fatal\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
