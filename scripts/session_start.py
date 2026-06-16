#!/usr/bin/env python3
"""HyperFocus Z0ne - Session Start Hook.

Writes a .focus_session_start marker, checks .env and core compose file,
and pings Redis if reachable.  Exits 0 on pass, 1 on hard failure.
"""

import socket
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SESSION_FILE = ROOT / ".focus_session_start"


def _redis_reachable() -> bool:
    try:
        s = socket.create_connection(("127.0.0.1", 6379), timeout=2)
        s.close()
        return True
    except OSError:
        return False


def main() -> int:
    now = datetime.now()
    print("\n[SESSION START] HyperFocus Z0ne")
    print("-" * 40)
    print("   Time : " + now.strftime("%Y-%m-%d %H:%M:%S"))

    SESSION_FILE.write_text(now.isoformat())

    env_ok = (ROOT / ".env").exists()
    core_ok = (ROOT / "docker-compose.core.yml").exists()
    redis_ok = _redis_reachable()

    print("   .env : " + ("PASS found" if env_ok else "WARN missing (.env)"))
    print("   core : " + ("PASS found" if core_ok else "FAIL docker-compose.core.yml missing"))
    print("   Redis: " + ("PASS reachable :6379" if redis_ok else "WARN offline (non-fatal)"))
    print()

    if not core_ok:
        print("FAIL  Session start FAILED -- docker-compose.core.yml not found.\n")
        return 1

    print("PASS  Session started. BROski forever! Let's build!\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
