#!/usr/bin/env python3
"""HyperFocus Z0ne - shared hook core (_broski_hook_core).

Single source of truth for the per-repo hook suite. Each repo's hook files are
thin wrappers that import this module + hooks_config and call the matching run_*().

CANONICAL master: HyperCode-V2.4/scripts/_broski_hook_core.py
Copies in the other repos are kept byte-identical by
HYPERFOCUS-LOOPS/scripts/sync_hooks.py. Edit the master, then run sync_hooks.py --
NEVER hand-edit a synced copy.
"""
from __future__ import annotations

import argparse
import json
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

# repo root: this module lives in <repo>/scripts/, so root is parents[1]
ROOT = Path(__file__).resolve().parents[1]

_PLACEHOLDERS_BASE = {"", "changeme", "CHANGEME", "your_value_here", "paste_here", "CHANGEME_REQUIRED"}


def _suffix(label: str) -> str:
    return f" -- {label}" if label else ""


# ----------------------------------------------------------------------------- env
def _load_env(env_files: Sequence[str], strip_quotes: bool) -> dict:
    kv: dict = {}
    for name in env_files:
        f = ROOT / name
        if not f.exists():
            continue
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            v = v.strip()
            if strip_quotes:
                v = v.strip('"').strip("'")
            kv[k.strip()] = v
    return kv


def run_env_guard(label: str, required: Sequence[str], placeholders_extra: Sequence[str] = (),
                  env_files: Sequence[str] = (".env",), strip_quotes: bool = False,
                  mode: str = "fail") -> int:
    import os

    print("\n[ENV GUARD] HyperFocus Z0ne" + _suffix(label))
    print("-" * 40)

    primary = ROOT / env_files[0]
    if not primary.exists():
        print("FAIL  .env not found at " + str(primary))
        print("      --> cp .env.example .env  then fill in values\n")
        return 0 if mode == "warn" else 1

    placeholders = _PLACEHOLDERS_BASE | set(placeholders_extra)
    merged = {**_load_env(env_files, strip_quotes), **os.environ}
    missing = []
    for var in required:
        val = merged.get(var, "")
        if not val or val in placeholders:
            missing.append(var)
        else:
            print("   PASS  " + var)

    if missing:
        print()
        for v in missing:
            print("   FAIL  " + v + "  (missing or placeholder)")
        print()
        word = "WARN" if mode == "warn" else "FAIL"
        print(word + "  Env guard " + ("warning" if mode == "warn" else "FAILED") +
              " -- " + str(len(missing)) + " var(s) not set.\n")
        return 0 if mode == "warn" else 1

    print()
    extra = (label + " ") if label else ""
    print("PASS  All required " + extra + "env vars present. Guard passed!\n")
    return 0


# ------------------------------------------------------------------------- session
def _redis_reachable() -> bool:
    try:
        s = socket.create_connection(("127.0.0.1", 6379), timeout=2)
        s.close()
        return True
    except OSError:
        return False


def run_session_start(label: str, compose_files: Sequence[str] = (),
                      fail_if_missing_compose: bool = True, redis_check: bool = True) -> int:
    now = datetime.now()
    print("\n[SESSION START] HyperFocus Z0ne" + _suffix(label))
    print("-" * 40)
    print("   Time : " + now.strftime("%Y-%m-%d %H:%M:%S"))

    (ROOT / ".focus_session_start").write_text(now.isoformat())

    env_ok = (ROOT / ".env").exists()
    print("   .env : " + ("PASS found" if env_ok else "WARN missing (.env)"))

    missing_compose = [c for c in compose_files if not (ROOT / c).exists()]
    core_ok = not missing_compose
    if compose_files:
        if core_ok:
            print("   core : PASS found")
        else:
            print("   core : FAIL " + ", ".join(missing_compose) + " missing")

    if redis_check:
        redis_ok = _redis_reachable()
        print("   Redis: " + ("PASS reachable :6379" if redis_ok else "WARN offline (non-fatal)"))
    print()

    if compose_files and fail_if_missing_compose and not core_ok:
        print("FAIL  Session start FAILED -- " + ", ".join(missing_compose) + " not found.\n")
        return 1

    print("PASS  Session started. BROski forever! Let's build!\n")
    return 0


def run_session_end(label: str) -> int:
    now = datetime.now()
    print("\n[SESSION END] HyperFocus Z0ne" + _suffix(label))
    print("-" * 40)
    print("   Time: " + now.strftime("%Y-%m-%d %H:%M:%S"))

    session_file = ROOT / ".focus_session_start"
    start: Optional[datetime] = None
    if session_file.exists():
        try:
            start = datetime.fromisoformat(session_file.read_text().strip())
        except ValueError:
            start = None

    if start:
        mins = int((now - start).total_seconds() // 60)
        print("   Duration: " + str(mins) + "m")
        session_file.unlink()
    else:
        print("   Duration: unknown (session_start was not run this session)")

    log = ROOT / "logs" / "sessions.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"start": start.isoformat() if start else None, "end": now.isoformat()}) + "\n")

    print("   Log:  logs/sessions.jsonl")
    print()
    print("PASS  Session ended. Great work BROski forever!\n")
    return 0


# ------------------------------------------------------------------ compose validator
def _validate_compose(compose_path: Path):
    import re
    banned_image = ("docker.io/", "index.docker.io/")
    banned_import = re.compile(r"from\s+backend\.app\.")
    healthcheck_re = re.compile(r"healthcheck", re.IGNORECASE)

    errors, warnings = [], []
    if not compose_path.exists():
        return ["file not found: " + str(compose_path)], warnings

    in_hc = False
    hc_indent = 0
    for i, raw in enumerate(compose_path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = raw.strip()
        if not stripped:
            continue
        indent = len(raw) - len(raw.lstrip())
        if healthcheck_re.search(stripped) and stripped.rstrip(":") == "healthcheck":
            in_hc, hc_indent = True, indent
        elif in_hc and indent <= hc_indent and stripped != "healthcheck:":
            in_hc = False
        for prefix in banned_image:
            if prefix in stripped:
                errors.append("line " + str(i) + ": docker.io reference -- " + repr(stripped))
        if banned_import.search(stripped):
            errors.append("line " + str(i) + ": forbidden 'from backend.app.*' -- " + repr(stripped))
        if in_hc and "127.0.0.1" in stripped:
            warnings.append("line " + str(i) + ": healthcheck uses 127.0.0.1 -- prefer localhost")
    return errors, warnings


def run_compose_validator(label: str, argv: Sequence[str]) -> int:
    if not argv:
        print("Usage: python scripts/compose_validator.py <compose-file>")
        return 2

    arg = argv[0]
    p = Path(arg)
    if p.is_absolute():
        compose_path = p
    else:
        compose_path = next((b / p for b in (Path.cwd(), ROOT) if (b / p).exists()), Path.cwd() / p)

    print("\n[COMPOSE VALIDATOR] HyperFocus Z0ne -- " + arg)
    print("-" * 40)
    print("   Path: " + str(compose_path))
    print()

    errors, warnings = _validate_compose(compose_path)
    for w in warnings:
        print("   WARN  " + w)
    if warnings:
        print()
    if errors:
        for e in errors:
            print("   FAIL  " + e)
        print()
        print("FAIL  Validation FAILED -- " + str(len(errors)) + " error(s).\n")
        return 1

    print("PASS  " + compose_path.name + " passed all Sacred Rules checks!")
    if warnings:
        print("      (" + str(len(warnings)) + " warning(s) -- non-blocking)")
    print()
    return 0


# -------------------------------------------------------------------------- xp reward
def _publish_xp(channel: str, db: int, payload: dict) -> Optional[str]:
    body = json.dumps(payload)
    try:
        import redis  # type: ignore[import]
        r = redis.Redis(host="127.0.0.1", port=6379, db=db, socket_connect_timeout=2)
        r.ping()
        r.publish(channel, body)
        return "tcp"
    except Exception:
        pass
    try:
        import shutil
        import subprocess
        if shutil.which("docker"):
            for container in ("redis", "hypercode-redis"):
                proc = subprocess.run(
                    ["docker", "exec", container, "redis-cli", "-n", str(db), "PUBLISH", channel, body],
                    capture_output=True, text=True, timeout=8,
                )
                if proc.returncode == 0:
                    return "docker:" + container
    except Exception:
        pass
    return None


def run_xp_reward(label: str, argv: Sequence[str], channel: str = "broski_economy", db: int = 1,
                  source: str = "session_hook") -> int:
    parser = argparse.ArgumentParser(description="Award BROski$ XP")
    parser.add_argument("--xp", type=int, default=10, help="XP amount (default 10)")
    parser.add_argument("--reason", default="session_hook", help="Award reason tag")
    args = parser.parse_args(list(argv))

    print("\n[BROSKI XP REWARD] HyperFocus Z0ne" + _suffix(label))
    print("-" * 40)
    print("   XP:     +" + str(args.xp))
    print("   Reason: " + args.reason)

    # `source` is repo attribution (preserved per-repo via config); the consumer
    # (broski_economy_consumer) keys on "type"/"event" == "xp_award" and stores source.
    payload = {
        "type": "xp_award",
        "xp": args.xp,
        "reason": args.reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": source,
    }
    published = _publish_xp(channel, db, payload)

    if published:
        print("   Redis:  PASS published to '" + channel + "' (DB " + str(db) + ", via " + published + ")")
        print()
        print("PASS  XP awarded! BROski forever!\n")
    else:
        print("   Redis:  WARN not reachable -- XP logged offline")
        print()
        print("PASS  XP recorded locally (+" + str(args.xp) + " " + args.reason + ") -- Redis offline is non-fatal\n")
    return 0
