#!/usr/bin/env python3
"""Build a bounded, local-only architecture inventory from a repository.

This tool never clones repositories, runs inspected code, contacts an LLM, reads
.env/secret files, or exports arbitrary source text. It extracts selected
structural metadata and emits a deterministic JSON inventory with provenance.

Schema 2 evidence fields (schema 1 used a single `sha256`, which was a hash of
the extracted metadata and not of the file):
  metadata_sha256  hash of the extracted, redacted metadata (path + kind + facts)
  content_sha256   hash of the file with CRLF normalised to LF, so a reviewer can
                   check it against the real file. It is withheld (null) when the
                   file looks secret-bearing, so a hash can never act as an oracle
                   for guessing a low-entropy secret.
Python modules (top level and one directory down, never tests) are parsed with
`ast` only: route decorators with literal paths and a fixed list of
security-relevant imports/calls are recorded. No source text is exported.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = 2
MAX_FILES = 20_000
MAX_DEPTH = 10
MAX_MANIFEST_BYTES = 256 * 1024
MAX_PYTHON_MODULES = 60
MAX_PYTHON_DEPTH = 1  # root (0) and direct subdirectories (1)
MAX_ROUTES_PER_MODULE = 100
TEST_DIR_NAMES = {"tests", "test", "__tests__"}
ROUTE_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "websocket"}
ROUTE_PATH_RE = re.compile(r"^/[A-Za-z0-9_{}./:-]{0,119}$")
# module top-level name -> category. Fixed allow-list: only these names are ever recorded.
SENSITIVE_IMPORTS = {
    "docker": "docker-client", "subprocess": "process-exec", "pty": "process-exec",
    "ctypes": "native-code", "pickle": "deserialization", "marshal": "deserialization",
    "shelve": "deserialization", "httpx": "network-client", "requests": "network-client",
    "aiohttp": "network-client", "urllib3": "network-client", "socket": "network-client",
    "cryptography": "crypto", "pyseto": "crypto", "jwt": "crypto", "nacl": "crypto",
}
DYNAMIC_EVAL_CALLS = {"eval", "exec", "compile"}
PROCESS_EXEC_ATTR_CALLS = {("os", "system"), ("os", "popen"), ("os", "execv"), ("os", "execvp"), ("os", "spawnl")}
# A line that assigns a literal value to a secret-looking key means the content hash is withheld.
SECRET_KEY_WORDS = ("password", "passwd", "secret", "token", "api_key", "apikey", "api-key", "private_key", "private-key", "credential")
SECRET_ASSIGN_RE = re.compile(r"""^\s*(?:-\s*)?['"]?([A-Za-z0-9_.-]+)['"]?\s*[:=]\s*(.+?)\s*$""")
URL_CREDENTIAL_RE = re.compile(r"://[^/@:\s]+:[^/@\s]+@")
BARE_SECRET_RE = re.compile(r"[A-Za-z0-9+/_=.:@-]{8,}")
IGNORE_DIRS = {
    ".git", ".hg", ".svn", ".venv", "venv", "env", "node_modules",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
    "dist", "build", "target", "vendor", "site-packages", "coverage",
    "htmlcov", ".next", "out", "output", "logs", "secrets", "secret",
    "backups", "DockerData", "HyperCodeData",
}
SECRET_FILE_RE = re.compile(r"(^|[._-])(secret|secrets|credential|credentials|token|password|private.?key)([._-]|$)", re.I)
PY_REQUIREMENT_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9_.-]*)")
DOCKERFILE_NAMES = {"Dockerfile", "Containerfile"}
PYTHON_MANIFESTS = {"pyproject.toml", "requirements.txt", "requirements-dev.txt", "Pipfile"}
NODE_MANIFESTS = {"package.json"}
GO_MANIFESTS = {"go.mod"}
RUST_MANIFESTS = {"Cargo.toml"}
COMPOSE_RE = re.compile(r"^(?:docker-)?compose(?:[._-].*)?\.ya?ml$|^docker-compose.*\.ya?ml$", re.I)


class ComposeSafeLoader(yaml.SafeLoader):
    """Safe loader that ignores Compose extension tags such as !override."""


def _construct_compose_extension(loader, tag_suffix: str, node):
    if isinstance(node, yaml.ScalarNode):
        return loader.construct_scalar(node)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node, deep=True)
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node, deep=True)
    raise yaml.constructor.ConstructorError(None, None, f"unsupported Compose !{tag_suffix} node", node.start_mark)


ComposeSafeLoader.add_multi_constructor("!", _construct_compose_extension)


def _safe_rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return "[outside-repository]"


def _is_test_module(name: str, rel_parts: tuple[str, ...]) -> bool:
    return name == "conftest.py" or name.startswith("test_") or name.endswith("_test.py") or any(part in TEST_DIR_NAMES for part in rel_parts)


def _walk_candidates(root: Path, max_files: int) -> tuple[list[Path], list[Path], int, bool]:
    """Return (manifest candidates, python module candidates, visited files, truncated)."""
    candidates: list[Path] = []
    python_modules: list[Path] = []
    visited = 0
    for current, dirs, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        rel_parts = current_path.relative_to(root).parts
        depth = len(rel_parts)
        dirs[:] = sorted(
            name for name in dirs
            if name not in IGNORE_DIRS
            and not name.startswith(".venv")
            and not (current_path / name).is_symlink()
        ) if depth < MAX_DEPTH else []
        for name in sorted(files):
            visited += 1
            if visited > max_files:
                return sorted(set(candidates)), sorted(set(python_modules)), visited - 1, True
            path = current_path / name
            if path.is_symlink() or SECRET_FILE_RE.search(name):
                continue
            if name.endswith(".py"):
                if depth <= MAX_PYTHON_DEPTH and not _is_test_module(name, rel_parts):
                    python_modules.append(path)
                continue
            if name in DOCKERFILE_NAMES or name.startswith("Dockerfile.") or name in PYTHON_MANIFESTS | NODE_MANIFESTS | GO_MANIFESTS | RUST_MANIFESTS or COMPOSE_RE.match(name):
                candidates.append(path)
    return sorted(set(candidates)), sorted(set(python_modules)), visited, False


def _metadata_fingerprint(path: str, kind: str, metadata: dict[str, Any]) -> str:
    """Hash extracted, redacted metadata only, never raw manifest bytes."""
    payload = json.dumps({"path": path, "kind": kind, "metadata": metadata}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _looks_secret_bearing(text: str, *, quoted_only: bool = False) -> bool:
    """True if the text assigns a literal to a secret-looking key or embeds URL credentials.

    Interpolations (${...}), *_FILE keys, /run/secrets paths and redaction markers do not count.
    quoted_only is for source code, where `token = f(x)` or `token: str` are not literals:
    only a quoted string literal counts. Config files (compose, .env) also count a bare word.
    """
    if URL_CREDENTIAL_RE.search(text):
        return True
    for line in text.splitlines():
        match = SECRET_ASSIGN_RE.match(line)
        if not match:
            continue
        key, raw_value = match.group(1).lower(), match.group(2).strip()
        if not any(word in key for word in SECRET_KEY_WORDS) or key.endswith(("_file", "-file")):
            continue
        quoted = raw_value[:1] in ("'", '"')
        value = raw_value.strip("'\"").strip()
        if quoted_only and not quoted:
            continue
        if not quoted and not BARE_SECRET_RE.fullmatch(value):
            continue
        if len(value) < 4 or value.startswith(("$", "/run/secrets", "[")) or value.lower() in {"redacted", "changeme", "none", "null", "true", "false"}:
            continue
        return True
    return False


def _content_fingerprint(data: bytes, text: str | None, *, is_source: bool = False) -> tuple[str | None, str | None]:
    """Return (content_sha256 over CRLF-normalised bytes, reason it was withheld)."""
    if text is None:
        return None, "non-utf8"
    if _looks_secret_bearing(text, quoted_only=is_source):
        return None, "secret-like-content"
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest(), None


def _entry(rel: str, kind: str, metadata: dict[str, Any], data: bytes, text: str | None) -> dict[str, Any]:
    content_sha256, withheld = _content_fingerprint(data, text, is_source=kind == "python-module")
    entry: dict[str, Any] = {
        "path": rel,
        "kind": kind,
        "metadata_sha256": _metadata_fingerprint(rel, kind, metadata),
        "content_sha256": content_sha256,
        "metadata": metadata,
    }
    if withheld:
        entry["content_sha256_withheld"] = withheld
    return entry


def _parse_python_module(text: str) -> dict[str, Any]:
    """Metadata only: literal route paths and allow-listed import/call categories. No source text."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError) as exc:
        return {"parse_error": type(exc).__name__}
    routes: set[tuple[str, str]] = set()
    imports: set[str] = set()
    dynamic_eval = False
    process_exec = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""] if node.level == 0 else []
        else:
            names = []
        for name in names:
            top = name.split(".", 1)[0]
            if top in SENSITIVE_IMPORTS:
                imports.add(f"{SENSITIVE_IMPORTS[top]}:{top}")
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in DYNAMIC_EVAL_CALLS:
                dynamic_eval = True
            if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
                if (func.value.id, func.attr) in PROCESS_EXEC_ATTR_CALLS or func.value.id == "subprocess":
                    process_exec = True
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute) and decorator.func.attr in ROUTE_METHODS and decorator.args:
                    first = decorator.args[0]
                    if isinstance(first, ast.Constant) and isinstance(first.value, str) and ROUTE_PATH_RE.fullmatch(first.value):
                        routes.add((decorator.func.attr.upper(), first.value))
    return {
        "routes": [{"method": m, "path": p} for m, p in sorted(routes)[:MAX_ROUTES_PER_MODULE]],
        "sensitive_imports": sorted(imports),
        "dynamic_eval": dynamic_eval,
        "process_exec_calls": process_exec,
    }


SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")


def _cap_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted({str(item).upper() for item in value if isinstance(item, str) and re.fullmatch(r"[A-Za-z_]{1,32}", item)})


def _safe_compose_value(value: str) -> str:
    if "${" in value:
        return "[compose-interpolated]"
    if re.search(r"(?i)://[^/@:]+:[^/@]+@", value):
        return "[credential-bearing-url]"
    return value

def _bounded_read(path: Path) -> bytes | None:
    try:
        if path.stat().st_size > MAX_MANIFEST_BYTES:
            return None
        return path.read_bytes()
    except OSError:
        return None


def _parse_compose(path: Path, text: str) -> dict[str, Any]:
    try:
        doc = yaml.load(text, Loader=ComposeSafeLoader) or {}
    except yaml.YAMLError as exc:
        return {"parse_error": type(exc).__name__, "services": []}
    if not isinstance(doc, dict):
        return {"parse_error": "non-object document", "services": []}
    services: list[dict[str, Any]] = []
    service_map = doc.get("services")
    if isinstance(service_map, dict):
        for name, raw in sorted(service_map.items(), key=lambda item: str(item[0])):
            if not isinstance(raw, dict):
                continue
            build = raw.get("build")
            if isinstance(build, str):
                build_info: dict[str, Any] = {"context": build}
            elif isinstance(build, dict):
                build_info = {key: build[key] for key in ("context", "dockerfile", "target") if isinstance(build.get(key), str)}
            else:
                build_info = {}
            ports = []
            for item in raw.get("ports", []) if isinstance(raw.get("ports", []), list) else []:
                if isinstance(item, int):
                    ports.append(str(item))
                elif isinstance(item, str):
                    ports.append(_safe_compose_value(item))
                elif isinstance(item, dict):
                    safe_port = {k: item[k] for k in ("target", "published", "protocol", "mode") if isinstance(item.get(k), (str, int))}
                    if safe_port:
                        ports.append(safe_port)
            networks = raw.get("networks", [])
            profiles = raw.get("profiles", [])
            depends = raw.get("depends_on", [])
            service_environment = raw.get("environment", {})
            if isinstance(service_environment, dict):
                environment_names = sorted(str(key) for key in service_environment)
            elif isinstance(service_environment, list):
                environment_names = sorted(
                    item.split("=", 1)[0]
                    for item in service_environment
                    if isinstance(item, str)
                )
            else:
                environment_names = []
            volumes = raw.get("volumes", [])
            docker_socket = any(
                "docker.sock" in (item if isinstance(item, str) else f"{item.get('source', '')}{item.get('target', '')}")
                for item in (volumes if isinstance(volumes, list) else [])
                if isinstance(item, (str, dict))
            )
            security_opt = raw.get("security_opt", [])
            no_new_privileges = any(
                isinstance(item, str) and item.lower().replace("=", ":").startswith("no-new-privileges") and not item.lower().endswith(":false")
                for item in (security_opt if isinstance(security_opt, list) else [])
            )
            raw_secrets = raw.get("secrets", [])
            secret_names = sorted({
                str(item.get("source") if isinstance(item, dict) else item)
                for item in (raw_secrets if isinstance(raw_secrets, list) else [])
                if isinstance(item, (str, dict))
                and SAFE_IDENTIFIER_RE.fullmatch(str(item.get("source") if isinstance(item, dict) else item))
            })
            services.append({
                "name": str(name),
                "read_only": raw.get("read_only") is True,
                "cap_drop": _cap_list(raw.get("cap_drop")),
                "cap_add": _cap_list(raw.get("cap_add")),
                "no_new_privileges": no_new_privileges,
                "privileged": raw.get("privileged") is True,
                "host_network": raw.get("network_mode") == "host",
                "docker_socket_mounted": docker_socket,
                "docker_host_env": "DOCKER_HOST" in environment_names,
                "secret_names": secret_names,
                "image": _safe_compose_value(raw["image"]) if isinstance(raw.get("image"), str) else None,
                "build": {key: _safe_compose_value(value) for key, value in build_info.items()},
                "ports": ports,
                "profiles": sorted(str(x) for x in profiles) if isinstance(profiles, list) else [],
                "networks": sorted(str(x) for x in (networks.keys() if isinstance(networks, dict) else networks)) if isinstance(networks, (dict, list)) else [],
                "depends_on": sorted(str(x) for x in (depends.keys() if isinstance(depends, dict) else depends)) if isinstance(depends, (dict, list)) else [],
                "environment_names": environment_names,
                "healthcheck": bool(raw.get("healthcheck")),
                "nonroot_hints": bool(raw.get("user") or raw.get("security_opt") or raw.get("cap_drop")),
            })
    return {"services": services, "includes": sorted(str(x) for x in doc.get("include", []) if isinstance(x, str)) if isinstance(doc.get("include"), list) else []}


def _parse_package_json(text: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return {"parse_error": type(exc).__name__}
    if not isinstance(data, dict):
        return {"parse_error": "non-object document"}
    deps: set[str] = set()
    for key in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
        value = data.get(key)
        if isinstance(value, dict):
            deps.update(str(name) for name in value)
    scripts = data.get("scripts")
    return {
        "name": data.get("name") if isinstance(data.get("name"), str) else None,
        "package_manager": data.get("packageManager") if isinstance(data.get("packageManager"), str) else None,
        "dependency_names": sorted(deps),
        "script_names": sorted(str(name) for name in scripts) if isinstance(scripts, dict) else [],
    }


def _parse_pyproject(text: str) -> dict[str, Any]:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        return {"parse_error": type(exc).__name__}
    project = data.get("project")
    if not isinstance(project, dict):
        return {"project_metadata_present": False}
    dependencies = project.get("dependencies", [])
    names = set()
    if isinstance(dependencies, list):
        for dependency in dependencies:
            match = PY_REQUIREMENT_RE.match(str(dependency))
            if match:
                names.add(match.group(1).lower().replace("_", "-"))
    return {
        "name": project.get("name") if isinstance(project.get("name"), str) else None,
        "version": project.get("version") if isinstance(project.get("version"), str) else None,
        "dependency_names": sorted(names),
    }


def _parse_python_requirements(text: str) -> list[str]:
    names = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "-", ".")):
            continue
        match = PY_REQUIREMENT_RE.match(stripped)
        if match:
            names.add(match.group(1).lower().replace("_", "-"))
    return sorted(names)


def _parse_dockerfile(text: str) -> dict[str, Any]:
    bases = []
    exposed = []
    users = []
    healthcheck = False
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = re.match(r"(?i)^FROM\s+(\S+)(?:\s+AS\s+(\S+))?", line)
        if match:
            bases.append({"image": match.group(1), "stage": match.group(2)})
            continue
        match = re.match(r"(?i)^EXPOSE\s+(.+)", line)
        if match:
            exposed.extend(port for port in match.group(1).split() if port.isdigit())
        match = re.match(r"(?i)^USER\s+(\S+)", line)
        if match:
            users.append(match.group(1))
        if re.match(r"(?i)^HEALTHCHECK\b", line):
            healthcheck = True
    return {"base_stages": bases, "exposed_ports": sorted(set(exposed)), "users": users, "healthcheck": healthcheck}


def build_inventory(root: Path, *, max_files: int = MAX_FILES) -> dict[str, Any]:
    if not 1 <= max_files <= 100_000:
        raise ValueError("max_files must be between 1 and 100000")
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"repository root is not a directory: {root}")
    candidates, python_candidates, visited, truncated_file_limit = _walk_candidates(root, max_files)
    manifests: list[dict[str, Any]] = []
    skipped_large: list[str] = []
    total_read = 0
    max_total = 4 * 1024 * 1024

    for path in candidates:
        data = _bounded_read(path)
        rel = _safe_rel(path, root)
        if data is None:
            skipped_large.append(rel)
            continue
        if total_read + len(data) > max_total:
            skipped_large.append(rel)
            continue
        total_read += len(data)
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            manifests.append(_entry(rel, "binary-or-non-utf8", {"size_bytes": len(data)}, data, None))
            continue
        if COMPOSE_RE.match(path.name):
            kind, metadata = "compose", _parse_compose(path, text)
        elif path.name in NODE_MANIFESTS:
            kind, metadata = "node", _parse_package_json(text)
        elif path.name in PYTHON_MANIFESTS:
            kind, metadata = "python", {"dependency_names": _parse_python_requirements(text)} if path.name.startswith("requirements") else (_parse_pyproject(text) if path.name == "pyproject.toml" else {"project_metadata_present": True})
        elif path.name in GO_MANIFESTS:
            module = next((line.split(maxsplit=1)[1] for line in text.splitlines() if line.startswith("module ") and len(line.split(maxsplit=1)) == 2), None)
            kind, metadata = "go", {"module": module}
        elif path.name in RUST_MANIFESTS:
            kind, metadata = "rust", {"manifest_present": True}
        else:
            kind, metadata = "dockerfile", _parse_dockerfile(text)
        manifests.append(_entry(rel, kind, metadata, data, text))

    # Python modules are best-effort extra signals: skipping one never makes the inventory incomplete.
    python_scanned = 0
    python_skipped = 0
    for path in python_candidates:
        if python_scanned >= MAX_PYTHON_MODULES:
            python_skipped += 1
            continue
        data = _bounded_read(path)
        if data is None or total_read + len(data) > max_total:
            python_skipped += 1
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            python_skipped += 1
            continue
        total_read += len(data)
        python_scanned += 1
        manifests.append(_entry(_safe_rel(path, root), "python-module", _parse_python_module(text), data, text))

    manifests.sort(key=lambda item: (item["path"], item["kind"]))
    file_list = [item["path"] for item in manifests]
    return {
        "schema_version": SCHEMA_VERSION,
        "source": {"kind": "local-directory", "name": root.name, "root_label": "."},
        "safety": {
            "repository_cloned": False,
            "code_executed": False,
            "llm_called": False,
            "secret_values_exported": False,
            "raw_source_exported": False,
        },
        "scan_limits": {
            "max_files": max_files,
            "max_depth": MAX_DEPTH,
            "max_manifest_bytes": MAX_MANIFEST_BYTES,
            "max_total_bytes": max_total,
            "visited_files": visited,
            "included_manifests": len(manifests),
            "python_modules_scanned": python_scanned,
            "python_modules_skipped": python_skipped,
            "skipped_large_manifests": sorted(skipped_large),
            "truncated_file_limit": truncated_file_limit,
            "inventory_complete": not truncated_file_limit and not skipped_large,
        },
        "files": file_list,
        "manifests": manifests,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path, help="Existing local repository directory; no cloning is performed")
    parser.add_argument("--output", type=Path, help="Optional JSON destination; defaults to stdout")
    parser.add_argument("--max-files", type=int, default=MAX_FILES)
    args = parser.parse_args(argv)
    if not 1 <= args.max_files <= 100_000:
        parser.error("--max-files must be between 1 and 100000")
    try:
        inventory = build_inventory(args.repository, max_files=args.max_files)
        serialized = json.dumps(inventory, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(serialized, encoding="utf-8")
        else:
            sys.stdout.write(serialized)
    except (OSError, ValueError) as exc:
        print(f"architecture inventory failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
