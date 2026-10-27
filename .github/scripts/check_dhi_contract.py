#!/usr/bin/env python3
"""Validate Docker Hardened Image source contracts for selected Compose services.

This is a static source gate, not proof that an image builds or runs. It validates
that each selected Compose service resolves to an explicitly configured Dockerfile
and checks the supported DHI, nonroot, healthcheck, and secret-context contracts.
"""
from __future__ import annotations

import argparse
import re
import sys
import tempfile
import subprocess
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_COMPOSE = ROOT / "docker-compose.hyperhealth.yml"


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _verify_entrypoint(entrypoint: Path) -> list[str]:
    """Run the real wrapper under mocked process replacement; never migrate or serve."""
    probe = '''
import os, runpy, subprocess, sys
class StopExec(Exception):
    pass
calls = []
def fake_run(argv, check=False):
    calls.append(("run", argv, check))
def fake_exec(executable, argv):
    calls.append(("exec", executable, argv))
    raise StopExec()
subprocess.run = fake_run
os.execvp = fake_exec
sys.argv = [r"ENTRY", *sys.argv[2:]]
try:
    runpy.run_path(r"ENTRY", run_name="__main__")
except StopExec:
    print(repr(calls))
'''.replace("ENTRY", str(entrypoint))
    with tempfile.NamedTemporaryFile("w", suffix=".py", encoding="utf-8", delete=False) as stream:
        stream.write(probe)
        probe_path = Path(stream.name)
    try:
        api = subprocess.run([sys.executable, str(probe_path), "probe", "api"], capture_output=True, text=True, check=False)
        worker = subprocess.run([sys.executable, str(probe_path), "probe", "python", "-m", "worker"], capture_output=True, text=True, check=False)
    finally:
        probe_path.unlink(missing_ok=True)
    errors = []
    if api.returncode != 0 or "alembic" not in api.stdout or "uvicorn" not in api.stdout:
        errors.append("API entrypoint must migrate before execing Uvicorn")
    if worker.returncode != 0 or "alembic" in worker.stdout or "worker" not in worker.stdout:
        errors.append("worker entrypoint must exec the Compose worker without running migrations")
    return errors


def _has_secret_exclusions(ignore_text: str) -> bool:
    entries = {line.strip().lower() for line in ignore_text.splitlines()}
    required = {".env", ".env.*", "secrets/", "*.key", "*.pem", "*.crt"}
    return required <= entries


def inspect_service(compose_path: Path, service_name: str) -> list[str]:
    errors: list[str] = []
    try:
        document = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return [f"cannot read Compose file {compose_path}: {exc}"]

    services = _dict(_dict(document).get("services"))
    service = _dict(services.get(service_name))
    if not service:
        return [f"service {service_name!r} is missing from {compose_path.relative_to(ROOT)}"]

    build = _dict(service.get("build"))
    if not build:
        return [f"{service_name}: missing build configuration"]
    context_raw = build.get("context")
    if not isinstance(context_raw, str) or not context_raw.strip():
        return [f"{service_name}: build.context must be a non-empty path"]
    context = (compose_path.parent / context_raw).resolve()
    if not context.is_dir():
        return [f"{service_name}: build context does not exist: {context}"]

    dockerfile_raw = build.get("dockerfile", "Dockerfile")
    if not isinstance(dockerfile_raw, str) or not dockerfile_raw.strip():
        return [f"{service_name}: build.dockerfile must be a non-empty path"]
    dockerfile = (context / dockerfile_raw).resolve()
    try:
        dockerfile.relative_to(context)
    except ValueError:
        return [f"{service_name}: Dockerfile resolves outside build context"]
    if not dockerfile.is_file():
        return [f"{service_name}: Dockerfile is missing: {dockerfile}"]

    try:
        dockerfile_text = dockerfile.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{service_name}: cannot read Dockerfile: {exc}"]

    from_images = re.findall(r"(?im)^\s*FROM\s+(\S+)(?:\s+AS\s+(\S+))?\s*$", dockerfile_text)
    if len(from_images) < 2:
        errors.append(f"{service_name}: expected separate DHI builder and runtime stages")
    else:
        builder = next((image for image, alias in from_images if (alias or "").lower() == "builder"), None)
        runtime = next((image for image, alias in from_images if (alias or "").lower() == "runtime"), None)
        if not builder or not runtime:
            errors.append(f"{service_name}: stage aliases builder/runtime are required")
        else:
            builder_match = re.fullmatch(r"dhi\.io/python:(\d+\.\d+\.\d+)-debian(\d+)-dev", builder)
            runtime_match = re.fullmatch(r"dhi\.io/python:(\d+\.\d+\.\d+)-debian(\d+)", runtime)
            if not builder_match:
                errors.append(f"{service_name}: builder must use a versioned DHI Python Debian -dev tag")
            if not runtime_match:
                errors.append(f"{service_name}: runtime must use the matching versioned DHI Python Debian runtime tag")
            if builder_match and runtime_match and builder_match.groups() != runtime_match.groups():
                errors.append(f"{service_name}: builder/runtime DHI Python version and Debian release must match")

    if not re.search(r"(?im)^\s*USER\s+(?:65532(?::65532)?|nonroot)\s*$", dockerfile_text):
        errors.append(f"{service_name}: runtime must explicitly run as DHI nonroot UID/GID 65532")
    if not re.search(r"(?im)^\s*ENTRYPOINT\s+\[\s*\"python\"\s*,\s*\"/app/entrypoint\.py\"\s*\]", dockerfile_text):
        errors.append(f"{service_name}: expected the shell-free Python entrypoint wrapper")
    else:
        entrypoint = context / "entrypoint.py"
        if not entrypoint.is_file():
            errors.append(f"{service_name}: missing entrypoint.py in build context")
        else:
            errors.extend(f"{service_name}: {failure}" for failure in _verify_entrypoint(entrypoint))
    if not re.search(r"(?im)^\s*HEALTHCHECK\b", dockerfile_text):
        errors.append(f"{service_name}: Dockerfile HEALTHCHECK is required")
    elif re.search(r"(?im)^\s*HEALTHCHECK.*\b(?:curl|wget)\b", dockerfile_text):
        errors.append(f"{service_name}: runtime healthcheck must not require curl/wget in minimal DHI runtime")

    ignore_path = context / ".dockerignore"
    if not ignore_path.is_file():
        errors.append(f"{service_name}: missing context-scoped .dockerignore")
    else:
        try:
            ignore_text = ignore_path.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"{service_name}: cannot read .dockerignore: {exc}")
        else:
            if not _has_secret_exclusions(ignore_text):
                errors.append(f"{service_name}: .dockerignore must exclude .env, secrets/, and key/certificate files")

    if service.get("read_only") is not True:
        errors.append(f"{service_name}: Compose service must set read_only: true")
    if "ALL" not in (service.get("cap_drop") or []):
        errors.append(f"{service_name}: Compose service must drop all capabilities")
    security_opt = service.get("security_opt") or []
    if "no-new-privileges:true" not in security_opt:
        errors.append(f"{service_name}: Compose service must set no-new-privileges:true")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compose", type=Path, default=DEFAULT_COMPOSE, help="Compose YAML containing the service")
    parser.add_argument("--service", action="append", dest="services", help="Service to inspect; may be repeated")
    parser.add_argument("--check", action="store_true", help="Run the source-contract check and exit nonzero on drift")
    args = parser.parse_args()
    compose_path = args.compose.resolve()
    services = args.services or ["hyperhealth-api", "hyperhealth-worker"]

    failures: list[str] = []
    for service_name in services:
        failures.extend(inspect_service(compose_path, service_name))

    if args.check:
        if failures:
            print("DHI SOURCE CONTRACT: FAIL")
            for error in failures:
                print(f"- {error}")
            return 1
        print(f"DHI SOURCE CONTRACT: PASS ({len(services)} service(s))")
        return 0

    if failures:
        print("DHI SOURCE CONTRACT: FAIL")
        for error in failures:
            print(f"- {error}")
        return 1

    print(f"DHI SOURCE CONTRACT: PASS ({len(services)} service(s))")
    print(f"- compose: {compose_path.relative_to(ROOT)}")
    print("- Build/runtime tags are paired and versioned")
    print("- Runtime is nonroot, shell-free, and has a Python healthcheck")
    print("- Compose is read-only, drops all caps, and sets no-new-privileges")
    print("- Context-scoped secret exclusions are present")
    print("- Image build/runtime behavior is NOT verified by this static check")
    return 0


if __name__ == "__main__":
    sys.exit(main())
