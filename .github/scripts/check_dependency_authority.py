#!/usr/bin/env python3
"""Validate the backend dependency authority chain.

The core runtime is defined by requirements.core.in, compiled to
requirements.core.txt, and consumed by the backend Dockerfile's core stage.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE_IN = ROOT / "backend" / "requirements.core.in"
CORE_TXT = ROOT / "backend" / "requirements.core.txt"
DOCKERFILE = ROOT / "backend" / "Dockerfile"

PACKAGE_LINE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9_.-]*)(?:\[[^]]+\])?(?:\s*[<>=!~].*)?(?:\s+#.*)?$")


def direct_packages(path: Path) -> set[str]:
    packages: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        match = PACKAGE_LINE.match(line)
        if match:
            packages.add(match.group(1).lower().replace("_", "-").replace(".", "-"))
    return packages


def main() -> int:
    errors: list[str] = []
    for path in (CORE_IN, CORE_TXT, DOCKERFILE):
        if not path.is_file():
            errors.append(f"missing required file: {path.relative_to(ROOT)}")

    if errors:
        print("DEPENDENCY AUTHORITY: FAIL")
        print("\n".join(f"- {error}" for error in errors))
        return 1

    source = direct_packages(CORE_IN)
    compiled = direct_packages(CORE_TXT)
    missing = sorted(source - compiled)
    if missing:
        errors.append("packages missing from requirements.core.txt: " + ", ".join(missing))

    docker = DOCKERFILE.read_text(encoding="utf-8")
    if "FROM python:3.12-slim" not in docker:
        errors.append("backend/Dockerfile must use python:3.12-slim")
    if "COPY requirements.core.txt ./" not in docker:
        errors.append("backend/Dockerfile core stage must copy requirements.core.txt")
    if "pip install -r requirements.core.txt" not in docker:
        errors.append("backend/Dockerfile core stage must install requirements.core.txt")

    if errors:
        print("DEPENDENCY AUTHORITY: FAIL")
        print("\n".join(f"- {error}" for error in errors))
        return 1

    print(f"DEPENDENCY AUTHORITY: PASS ({len(source)} core packages)")
    print("- source: backend/requirements.core.in")
    print("- compiled: backend/requirements.core.txt")
    print("- consumer: backend/Dockerfile core stage")
    print("- runtime: Python 3.12")
    return 0


if __name__ == "__main__":
    sys.exit(main())
