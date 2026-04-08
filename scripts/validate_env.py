#!/usr/bin/env python3
"""
HyperCode V2.0 — .env Startup Validator

Run before launching services to catch missing or empty required vars.
Usage: python scripts/validate_env.py
"""

import os
import sys
from pathlib import Path

# ── Required vars — system won't work without these ──────────────────────────
REQUIRED = [
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "REDIS_URL",
    "SECRET_KEY",
]

# ── Recommended vars — degraded mode if missing ───────────────────────────────
RECOMMENDED = [
    "OPENAI_API_KEY",
    "PERPLEXITY_API_KEY",
    "GF_SECURITY_ADMIN_USER",
    "GF_SECURITY_ADMIN_PASSWORD",
    "ANTHROPIC_API_KEY",
]


def load_env_file(env_path: Path) -> dict:
    """Parse a .env file into a dict (ignores comments + blank lines)."""
    env_vars = {}
    if not env_path.exists():
        return env_vars
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env_vars[key.strip()] = value.strip()
    return env_vars


def validate() -> bool:
    root = Path(__file__).parent.parent
    env_path = root / ".env"

    print("\n🔍 HyperCode .env Validator\n" + "─" * 40)

    if not env_path.exists():
        print("❌  .env file NOT FOUND")
        print("   → Run: cp .env.example .env  then fill in your values\n")
        return False

    file_vars = load_env_file(env_path)
    # Merge with actual environment (os.environ takes priority)
    merged = {**file_vars, **os.environ}

    errors, warnings = [], []

    for var in REQUIRED:
        val = merged.get(var, "")
        if not val or val in ("your_value_here", "changeme", "CHANGEME", ""):
            errors.append(var)

    for var in RECOMMENDED:
        val = merged.get(var, "")
        if not val or val in ("your_value_here", "changeme", "CHANGEME", ""):
            warnings.append(var)

    # ── Print results ─────────────────────────────────────────────────────────
    if errors:
        print("🔴  MISSING REQUIRED VARS (system will NOT start):")
        for v in errors:
            print(f"   ✗  {v}")
        print()

    if warnings:
        print("🟡  MISSING RECOMMENDED VARS (degraded mode):")
        for v in warnings:
            print(f"   ⚠  {v}")
        print()

    ok_required = [v for v in REQUIRED if v not in errors]
    for v in ok_required:
        print(f"   ✅  {v}")

    print()
    if errors:
        print(f"❌  Validation FAILED — {len(errors)} required var(s) missing.")
        print("   Fix your .env then re-run this script.\n")
        return False

    print("✅  All required vars present. You're good to launch! 🚀\n")
    return True


if __name__ == "__main__":
    ok = validate()
    sys.exit(0 if ok else 1)
