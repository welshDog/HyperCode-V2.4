#!/usr/bin/env python3
"""HyperFocus Z0ne - Compose Validator.

Enforces Sacred Rules on a docker-compose file:
  - NEVER docker.io image references
  - NEVER 'from backend.app.' in inline commands
  - WARN if healthcheck uses 127.0.0.1 (should be localhost -- IPv6 fix)

Usage:
    python scripts/compose_validator.py docker-compose.core.yml
    python scripts/compose_validator.py /abs/path/to/compose.yml
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_BANNED_IMAGE_PREFIXES = ("docker.io/", "index.docker.io/")
_BANNED_IMPORT_RE = re.compile(r"from\s+backend\.app\.")
_HEALTHCHECK_RE = re.compile(r"healthcheck", re.IGNORECASE)


def _resolve_compose(arg):
    p = Path(arg)
    if p.is_absolute():
        return p
    for base in (Path.cwd(), ROOT):
        candidate = base / p
        if candidate.exists():
            return candidate
    return Path.cwd() / p


def validate(compose_path):
    errors = []
    warnings = []

    if not compose_path.exists():
        errors.append("file not found: " + str(compose_path))
        return errors, warnings

    in_healthcheck = False

    for i, raw in enumerate(compose_path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = raw.strip()

        if _HEALTHCHECK_RE.search(stripped):
            in_healthcheck = True
        elif stripped and not raw[0:1] in (" ", "\t"):
            in_healthcheck = False

        for prefix in _BANNED_IMAGE_PREFIXES:
            if prefix in stripped:
                errors.append("line " + str(i) + ": docker.io reference -- " + repr(stripped))

        if _BANNED_IMPORT_RE.search(stripped):
            errors.append("line " + str(i) + ": forbidden 'from backend.app.*' -- " + repr(stripped))

        if in_healthcheck and "127.0.0.1" in stripped:
            warnings.append("line " + str(i) + ": healthcheck uses 127.0.0.1 -- prefer localhost")

    return errors, warnings


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/compose_validator.py <compose-file>")
        return 2

    compose_path = _resolve_compose(sys.argv[1])

    print("\n[COMPOSE VALIDATOR] HyperFocus Z0ne -- " + sys.argv[1])
    print("-" * 40)
    print("   Path: " + str(compose_path))
    print()

    errors, warnings = validate(compose_path)

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


if __name__ == "__main__":
    sys.exit(main())
