#!/usr/bin/env python3
"""HyperFocus Z0ne - Env Guard.

Blocks launch if required vars are absent or set to placeholder values.
Reads .env from repo root and merges with os.environ (env takes priority).
Exits 0 on pass, 1 on failure.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "REDIS_URL",
    "SECRET_KEY",
]

_PLACEHOLDERS = {"", "changeme", "CHANGEME", "your_value_here", "paste_here", "CHANGEME_REQUIRED"}


def _load_env(env_path):
    kv = {}
    if not env_path.exists():
        return kv
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        kv[k.strip()] = v.strip()
    return kv


def main() -> int:
    print("\n[ENV GUARD] HyperFocus Z0ne")
    print("-" * 40)

    env_path = ROOT / ".env"
    if not env_path.exists():
        print("FAIL  .env not found at " + str(env_path))
        print("      --> cp .env.example .env  then fill in values\n")
        return 1

    merged = {**_load_env(env_path), **os.environ}
    missing = []

    for var in REQUIRED:
        val = merged.get(var, "")
        if not val or val in _PLACEHOLDERS:
            missing.append(var)
        else:
            print("   PASS  " + var)

    if missing:
        print()
        for v in missing:
            print("   FAIL  " + v + "  (missing or placeholder)")
        print()
        print("FAIL  Env guard FAILED -- " + str(len(missing)) + " var(s) not set.\n")
        return 1

    print()
    print("PASS  All required env vars present. Guard passed!\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
