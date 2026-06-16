#!/usr/bin/env python3
"""HyperFocus Z0ne - Session End Hook.

Reads the .focus_session_start marker written by session_start.py,
computes duration, appends a JSONL record to logs/sessions.jsonl,
and removes the marker.  Always exits 0.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
SESSION_FILE = ROOT / ".focus_session_start"
SESSION_LOG = ROOT / "logs" / "sessions.jsonl"


def _read_start() -> Optional[datetime]:
    if not SESSION_FILE.exists():
        return None
    try:
        return datetime.fromisoformat(SESSION_FILE.read_text().strip())
    except ValueError:
        return None


def main() -> int:
    now = datetime.now()
    print("\n[SESSION END] HyperFocus Z0ne")
    print("-" * 40)
    print("   Time: " + now.strftime("%Y-%m-%d %H:%M:%S"))

    start = _read_start()
    if start:
        mins = int((now - start).total_seconds() // 60)
        print("   Duration: " + str(mins) + "m")
        SESSION_FILE.unlink()
    else:
        print("   Duration: unknown (session_start was not run this session)")

    SESSION_LOG.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "start": start.isoformat() if start else None,
        "end": now.isoformat(),
    }
    with SESSION_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")

    print("   Log:  logs/sessions.jsonl")
    print()
    print("PASS  Session ended. Great work BROski forever!\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
