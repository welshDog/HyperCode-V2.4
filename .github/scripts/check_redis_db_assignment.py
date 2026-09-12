#!/usr/bin/env python3
"""Fail if throttle-agent's REDIS_URL isn't on Redis DB 1 (rate limits).

Sacred Rule (CLAUDE.md): Redis DB 1/DB 2 assignments must never be mixed
between services.

Replaces a `grep -A5 "throttle-agent" docker-compose.agents-full.yml | grep
"REDIS_URL" | grep -v "redis:6379/1"` chain (health-check.yml, pre-2026-09-12)
that was broken two ways: (1) `grep -A5` finds the FIRST line containing the
substring "throttle-agent" in the whole file, which after this session's
restore is a header comment, not the service block, so the 5-line window it
captured never actually contained a REDIS_URL line; (2) even when it does
land on the right block, the literal substring "redis:6379/1" never matches
the repo's actual convention `redis://${REDIS_HOST:-redis}:6379/1` -- the
`${REDIS_HOST:-redis}` indirection (established 2026-08-23, see
fleet_registry.py) puts a `}` between "redis" and ":6379", so the exact
substring the old check looked for never appears in a real, correct line.

This parses the real compose service block instead of a text window, and
checks only the trailing `:6379/<N>` database number, independent of host.
"""
import re
import sys

import yaml

DB_RE = re.compile(r":6379/(\d+)\b")


def main() -> int:
    print("Checking Redis DB assignments in compose files...")

    with open("docker-compose.agents-full.yml", encoding="utf-8") as f:
        doc = yaml.safe_load(f)

    svc = (doc.get("services") or {}).get("throttle-agent")
    if svc is None:
        print("FAIL: throttle-agent service not found in docker-compose.agents-full.yml")
        return 1

    env = svc.get("environment") or []
    env_text = " ".join(env) if isinstance(env, list) else " ".join(f"{k}={v}" for k, v in env.items())

    match = None
    for line in env_text.split():
        if "REDIS_URL" in line:
            db_match = DB_RE.search(line)
            if db_match:
                match = db_match
                break

    if match is None:
        print("FAIL: throttle-agent has no REDIS_URL with a :6379/<N> database number")
        return 1

    if match.group(1) != "1":
        print(f"FAIL: throttle-agent must use Redis DB 1 (rate limits) -- found DB {match.group(1)}")
        return 1

    print("PASS: throttle-agent Redis DB 1 confirmed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
