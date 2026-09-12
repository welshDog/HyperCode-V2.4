#!/usr/bin/env python3
"""Fail if a real docker.io / index.docker.io registry reference exists in a
compose or Kubernetes YAML `image:` line, or a docker.io apt-package install
exists in a shell script.

Sacred Rule (CLAUDE.md): `docker-ce-cli` — NEVER `docker.io` for socket
agents — agent connectivity depends on it. That rule is about the Debian apt
package `docker.io` vs `docker-ce-cli` for containers that talk to
/var/run/docker.sock, plus the closely related concern of not pulling
container images from the docker.io/index.docker.io registry hostname when
GHCR is the project's real registry.

Replaces a bare `grep -r "docker.io"` (health-check.yml, pre-2026-09-12) that
substring-matched comments, docstrings, rule-restatements, and test fixtures
with no scoping at all — see docs/upgrades/ CI investigation for the full
false-positive inventory this was validated against.

Scope, deliberately narrow:
  - *.yml / *.yaml: only `image:` mapping-key lines (skips comments, skips
    any other non-image mention of the string).
  - *.sh: literal docker.io on a non-comment line (apt-install guard;
    currently zero matches repo-wide, this is a forward guard not an active
    catch).
  - Drops *.py entirely — every known false positive lives in a .py file
    (string literals, docstrings, comments, test fixtures); none of the real
    catches are .py.
  - Excludes .github/ (workflow YAML legitimately names this rule in step
    text and carries no image:/apt-install lines to check), tests/
    (fixtures that intentionally exercise this exact rule), and common
    vendored/VCS directories.
  - Does NOT scan Dockerfile* — a real `FROM docker.io/library/...` base
    image question there is a separate, unresolved decision, not a
    mechanical fix.
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path.cwd()

EXCLUDED_DIR_NAMES = {
    ".git",
    ".github",
    "tests",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
}

IMAGE_LINE_RE = re.compile(r"^\s*(-\s+)?image:\s*.*(docker\.io|index\.docker\.io)", re.IGNORECASE)
SH_DOCKERIO_RE = re.compile(r"docker\.io")


def _is_excluded_dir(name: str) -> bool:
    return name in EXCLUDED_DIR_NAMES or name.startswith(".venv")


def _scan_yaml(path: Path, errors: list) -> None:
    for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        if IMAGE_LINE_RE.match(line):
            errors.append(f"{path.relative_to(ROOT)}:{i}: {line.strip()}")


def _scan_sh(path: Path, errors: list) -> None:
    for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if SH_DOCKERIO_RE.search(stripped):
            errors.append(f"{path.relative_to(ROOT)}:{i}: {stripped}")


SCANNERS = {
    ".yml": _scan_yaml,
    ".yaml": _scan_yaml,
    ".sh": _scan_sh,
}


def main() -> int:
    print("Checking for forbidden docker.io references (image: lines + shell installs)...")
    errors = []

    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if not _is_excluded_dir(d)]
        for filename in filenames:
            scanner = SCANNERS.get(Path(filename).suffix)
            if scanner is None:
                continue
            scanner(Path(dirpath) / filename, errors)

    if errors:
        print("FAIL: docker.io found! Use docker-ce-cli / ghcr.io only.")
        for e in sorted(set(errors)):
            print("  " + e)
        return 1

    print("PASS: No forbidden docker.io references found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
