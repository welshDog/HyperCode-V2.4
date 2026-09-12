#!/usr/bin/env python3
"""Fail if any real `from backend.app...` import exists in a Python file.

Sacred Rule (CLAUDE.md): `from app.X import Y` — NEVER `from backend.app.X` —
import path convention.

Replaces a bare `grep -r "from backend\\.app" --include="*.py" .`
(health-check.yml, pre-2026-09-12) that substring-matched the rule's own
restatement inside docstrings, comments, string literals, and error messages
with no scoping at all — e.g. `scripts/compose_validator.py`'s docstring
describing what it enforces, `scripts/_broski_hook_core.py`'s own error
message, `agents/crew-orchestrator/crew_v2.py`'s agent backstory string, and
`tests/test_compose_validator.py`'s fixture command string.

Scope: only lines that, after leading whitespace, literally start with
`from backend.app` — a real Python import statement always starts a logical
line this way; every known false positive above has the phrase appear
mid-line (inside a string, docstring, or comment), never at line start.
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path.cwd()

EXCLUDED_DIR_NAMES = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
}

IMPORT_RE = re.compile(r"^\s*from backend\.app\b")


def _is_excluded_dir(name: str) -> bool:
    return name in EXCLUDED_DIR_NAMES or name.startswith(".venv")


def _scan(path: Path, errors: list) -> None:
    for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        if IMPORT_RE.match(line):
            errors.append(f"{path.relative_to(ROOT)}:{i}: {line.strip()}")


def main() -> int:
    print("Checking for forbidden 'from backend.app' imports...")
    errors = []

    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if not _is_excluded_dir(d)]
        for filename in filenames:
            if filename.endswith(".py"):
                _scan(Path(dirpath) / filename, errors)

    if errors:
        print("FAIL: 'from backend.app' import found! Use 'from app.X import Y'.")
        for e in sorted(set(errors)):
            print("  " + e)
        return 1

    print("PASS: No forbidden imports found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
