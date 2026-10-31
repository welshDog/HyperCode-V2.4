#!/usr/bin/env python3
"""Turn an approved local architecture inventory into reviewable pattern candidates.

No cloning, source execution, network access, LLM calls, or deployment occurs.
The input must be an architecture_inventory.py JSON file and an explicit
human approval JSON bound to that exact inventory digest and source name.
Output is a deterministic candidate report, never executable build instructions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
SAFE_SERVICE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")
APPROVAL_SCHEMA = "hypercode.source-approval.v1"
OUTPUT_SCHEMA = "hypercode.pattern-review.v1"


def canonical_digest(value: dict[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {label}: {type(exc).__name__}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} root must be a JSON object")
    return value


SUPPORTED_INVENTORY_SCHEMAS = (1, 2)


def _evidence(manifest: dict[str, Any], schema_version: int) -> dict[str, Any]:
    """Evidence reference for a packet. Schema 1 inventories only have a metadata fingerprint.

    `sha256` is kept in every packet because older readers (the dashboard parser) require it;
    it is ALWAYS the metadata fingerprint, never a file hash. Use content_sha256 to check the file.
    """
    if schema_version == 1:
        return {"path": manifest["path"], "sha256": manifest["sha256"]}
    return {
        "path": manifest["path"],
        "sha256": manifest["metadata_sha256"],
        "metadata_sha256": manifest["metadata_sha256"],
        "content_sha256": manifest.get("content_sha256"),
    }


def validate_approval(inventory: dict[str, Any], approval: dict[str, Any]) -> dict[str, str]:
    schema_version = inventory.get("schema_version")
    if schema_version not in SUPPORTED_INVENTORY_SCHEMAS:
        raise ValueError("unsupported inventory schema_version")
    source = inventory.get("source")
    safety = inventory.get("safety")
    manifests = inventory.get("manifests")
    limits = inventory.get("scan_limits")
    if not isinstance(limits, dict) or limits.get("inventory_complete") is not True:
        raise ValueError("incomplete inventory cannot be approved for pattern review")
    if not isinstance(source, dict) or source.get("kind") != "local-directory":
        raise ValueError("inventory source must be local-directory")
    source_name = source.get("name")
    if not isinstance(source_name, str) or not SAFE_NAME.fullmatch(source_name):
        raise ValueError("inventory source name is invalid")
    if not isinstance(safety, dict) or any(safety.get(key) is not False for key in ("repository_cloned", "code_executed", "llm_called", "raw_source_exported")):
        raise ValueError("inventory safety claims are missing or unsafe")
    if not isinstance(manifests, list) or len(manifests) > 20_000:
        raise ValueError("inventory manifests must be a bounded list")

    for item in manifests:
        if not isinstance(item, dict):
            raise ValueError("inventory contains a malformed manifest entry")
        path = item.get("path")
        digest = item.get("sha256" if schema_version == 1 else "metadata_sha256")
        if not isinstance(path, str) or path.startswith(("/", "\\")) or ".." in Path(path).parts:
            raise ValueError("inventory contains a non-repository manifest path")
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            raise ValueError("inventory contains an invalid metadata fingerprint")
        if schema_version == 2:
            content_digest = item.get("content_sha256")
            if content_digest is not None and (not isinstance(content_digest, str) or not SHA256.fullmatch(content_digest)):
                raise ValueError("inventory contains an invalid content fingerprint")
        if "content" in item or "raw_source" in item:
            raise ValueError("inventory must not contain raw source text")

    if approval.get("schema_version") != APPROVAL_SCHEMA:
        raise ValueError(f"approval schema_version must be {APPROVAL_SCHEMA}")
    if approval.get("approved") is not True:
        raise ValueError("source has no explicit human approval")
    if approval.get("source_name") != source_name:
        raise ValueError("approval source_name does not match inventory")
    expected_digest = canonical_digest(inventory)
    if approval.get("inventory_sha256") != expected_digest:
        raise ValueError("approval does not match this exact inventory digest")
    reviewer = approval.get("approved_by")
    approved_at = approval.get("approved_at")
    approval_id = approval.get("approval_id")
    if not all(isinstance(value, str) and value.strip() for value in (reviewer, approved_at, approval_id)):
        raise ValueError("approval must include approval_id, approved_by, and approved_at")
    if len(reviewer) > 120 or len(approved_at) > 80 or len(approval_id) > 120:
        raise ValueError("approval metadata exceeds allowed length")
    return {
        "approval_id": approval_id.strip(),
        "approved_by": reviewer.strip(),
        "approved_at": approved_at.strip(),
        "inventory_sha256": expected_digest,
    }


def _safe_service_name(value: Any) -> str | None:
    return value if isinstance(value, str) and SAFE_SERVICE.fullmatch(value) else None


def extract_candidates(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    """Produce deterministic, evidence-linked candidates from allowlisted metadata only."""
    manifests = inventory["manifests"]
    version = inventory["schema_version"]
    candidates: list[dict[str, Any]] = []
    compose_services: list[tuple[str, str, dict[str, Any]]] = []
    languages: set[str] = set()

    for manifest in manifests:
        path = manifest["path"]
        kind = manifest.get("kind")
        metadata = manifest.get("metadata")
        if not isinstance(metadata, dict):
            continue
        if kind == "compose":
            services = metadata.get("services")
            if isinstance(services, list):
                for service in services:
                    if not isinstance(service, dict):
                        continue
                    name = _safe_service_name(service.get("name"))
                    if name:
                        compose_services.append((path, name, service))
        elif kind in {"python", "node", "go", "rust"}:
            languages.add(kind)

    if compose_services:
        links = []
        for path, name, service in compose_services:
            dependencies = service.get("depends_on", [])
            if isinstance(dependencies, list):
                for dependency in dependencies:
                    dep = _safe_service_name(dependency)
                    if dep:
                        links.append({"from": name, "to": dep, "source": path})
        candidates.append({
            "candidate_id": "compose-service-topology",
            "category": "service-architecture",
            "claim": "Compose defines a service topology suitable for human review.",
            "evidence": [_evidence(manifest, version) for manifest in manifests if manifest.get("kind") == "compose"],
            "facts": {"service_names": sorted({name for _, name, _ in compose_services}), "dependency_edges": sorted(links, key=lambda edge: (edge["from"], edge["to"], edge["source"]))},
            "limitations": ["Compose declarations do not prove runtime health or dependency correctness."],
        })

    dockerfiles = [item for item in manifests if item.get("kind") == "dockerfile" and isinstance(item.get("metadata"), dict)]
    if dockerfiles:
        multi_stage = [item["path"] for item in dockerfiles if len(item["metadata"].get("base_stages", [])) > 1]
        nonroot = [item["path"] for item in dockerfiles if item["metadata"].get("users")]
        healthchecks = [item["path"] for item in dockerfiles if item["metadata"].get("healthcheck") is True]
        candidates.append({
            "candidate_id": "container-build-hardening-signals",
            "category": "container-pattern",
            "claim": "Dockerfiles expose build-stage, user, and healthcheck signals for review.",
            "evidence": [_evidence(item, version) for item in dockerfiles],
            "facts": {"dockerfile_count": len(dockerfiles), "multi_stage_paths": sorted(multi_stage), "user_declared_paths": sorted(nonroot), "healthcheck_paths": sorted(healthchecks)},
            "limitations": ["A USER or HEALTHCHECK declaration is a static hint, not proof of least privilege or a passing runtime check."],
        })

    if languages:
        candidates.append({
            "candidate_id": "declared-language-ecosystems",
            "category": "technology-stack",
            "claim": "The repository contains these supported package-manifest families.",
            "evidence": [_evidence(item, version) for item in manifests if item.get("kind") in {"python", "node", "go", "rust"}],
            "facts": {"manifest_families": sorted(languages)},
            "limitations": ["Manifest presence does not prove deployed or actively used runtime components."],
        })

    if version >= 2:
        candidates.extend(_security_candidates(manifests, compose_services, version))
    return candidates


MAX_EVIDENCE = 80  # the review UI rejects a candidate that cites more than this
MAX_LISTED = 100


def _capped(items: list[Any]) -> tuple[list[Any], bool]:
    return items[:MAX_LISTED], len(items) > MAX_LISTED


def _security_candidates(manifests: list[dict[str, Any]], compose_services: list[tuple[str, str, dict[str, Any]]], version: int) -> list[dict[str, Any]]:
    """Schema 2 signals: compose hardening, capability boundary, HTTP surface. Static hints only."""
    out: list[dict[str, Any]] = []
    compose_manifests = [m for m in manifests if m.get("kind") == "compose"]
    modules = [m for m in manifests if m.get("kind") == "python-module" and isinstance(m.get("metadata"), dict)]

    def services_where(flag: str) -> list[str]:
        return sorted({name for _, name, svc in compose_services if svc.get(flag) is True})

    def evidence_for(items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
        refs = [_evidence(item, version) for item in items]
        return refs[:MAX_EVIDENCE], len(refs) > MAX_EVIDENCE

    if compose_services:
        evidence, evidence_truncated = evidence_for(compose_manifests)
        read_only, ro_cut = _capped(services_where("read_only"))
        no_new_priv, nnp_cut = _capped(services_where("no_new_privileges"))
        drop_all, drop_cut = _capped(sorted({name for _, name, svc in compose_services if "ALL" in (svc.get("cap_drop") or [])}))
        with_secrets, sec_cut = _capped(sorted({name for _, name, svc in compose_services if svc.get("secret_names")}))
        out.append({
            "candidate_id": "compose-hardening-declarations",
            "category": "container-pattern",
            "claim": "Compose services declare these runtime hardening options.",
            "evidence": evidence,
            "facts": {
                "service_count": len({name for _, name, _ in compose_services}),
                "read_only_services": read_only,
                "cap_drop_all_services": drop_all,
                "no_new_privileges_services": no_new_priv,
                "services_using_secrets": with_secrets,
                "lists_truncated": any((ro_cut, nnp_cut, drop_cut, sec_cut)),
                "evidence_truncated": evidence_truncated,
            },
            "limitations": ["Declared options are static hints; they do not prove the running container has them, and options inherited from other compose files are not merged."],
        })

    if compose_services or modules:
        evidence, evidence_truncated = evidence_for(compose_manifests + modules)
        by_category: dict[str, list[str]] = {}
        for module in modules:
            for entry in module["metadata"].get("sensitive_imports", []):
                category = str(entry).split(":", 1)[0]
                by_category.setdefault(category, []).append(module["path"])
        dynamic_eval = sorted(m["path"] for m in modules if m["metadata"].get("dynamic_eval") is True)
        process_exec = sorted(m["path"] for m in modules if m["metadata"].get("process_exec_calls") is True)
        out.append({
            "candidate_id": "capability-boundary-signals",
            "category": "security-boundary",
            "claim": "These static signals show which risky capabilities the scanned compose services and Python modules declare or use.",
            "evidence": evidence,
            "facts": {
                "docker_socket_services": services_where("docker_socket_mounted"),
                "docker_host_env_services": services_where("docker_host_env"),
                "privileged_services": services_where("privileged"),
                "host_network_services": services_where("host_network"),
                "cap_add_services": sorted({name for _, name, svc in compose_services if svc.get("cap_add")}),
                "python_modules_scanned": len(modules),
                "python_modules_by_import_category": {key: sorted(set(paths)) for key, paths in sorted(by_category.items())},
                "dynamic_eval_modules": dynamic_eval,
                "process_exec_modules": process_exec,
                "evidence_truncated": evidence_truncated,
            },
            "limitations": [
                "An empty list means the scan found nothing, not that the capability is impossible.",
                "Only top-level Python modules and one directory down are parsed; tests, generated code and dynamic imports are not seen.",
            ],
        })

    if modules:
        evidence, evidence_truncated = evidence_for(modules)
        routes = sorted(
            ({"method": r["method"], "path": r["path"], "module": m["path"]}
             for m in modules for r in m["metadata"].get("routes", []) if isinstance(r, dict) and "method" in r and "path" in r),
            key=lambda r: (r["module"], r["path"], r["method"]),
        )
        listed, routes_cut = _capped(routes)
        out.append({
            "candidate_id": "python-module-surface",
            "category": "service-surface",
            "claim": "Scanned Python modules declare these HTTP routes.",
            "evidence": evidence,
            "facts": {
                "modules_scanned": len(modules),
                "modules_with_routes": sorted({r["module"] for r in routes}),
                "routes_total": len(routes),
                "routes": listed,
                "routes_truncated": routes_cut,
                "evidence_truncated": evidence_truncated,
            },
            "limitations": ["Only route decorators with a literal path are seen; routers mounted elsewhere, middleware and auth dependencies are not evaluated."],
        })
    return out


def build_review(inventory: dict[str, Any], approval: dict[str, Any]) -> dict[str, Any]:
    approval_record = validate_approval(inventory, approval)
    source = inventory["source"]["name"]
    candidates = extract_candidates(inventory)
    return {
        "schema_version": 1,
        "document_type": OUTPUT_SCHEMA,
        "source": {"kind": "local-directory", "name": source},
        "provenance": {
            **approval_record,
            "inventory_schema_version": inventory["schema_version"],
            "manifest_count": len(inventory["manifests"]),
            "extractor": "scripts/pattern_review.py",
        },
        "review_status": "pending_human_review",
        "synthesis_authorized": False,
        "execution_authorized": False,
        "candidate_patterns": candidates,
        "review_instructions": [
            "Confirm each claim against the cited manifest evidence.",
            "Reject patterns derived from untrusted or irrelevant repositories.",
            "A reviewer must explicitly approve a specific pattern before any future synthesis stage consumes it.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory", type=Path, help="architecture_inventory.py JSON output")
    parser.add_argument("--approval", type=Path, required=True, help="Human-reviewed approval JSON bound to the inventory digest")
    parser.add_argument("--output", type=Path, required=True, help="Output JSON review packet")
    args = parser.parse_args(argv)
    try:
        inventory = _load_json(args.inventory, "inventory")
        approval = _load_json(args.approval, "approval")
        review = build_review(inventory, approval)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(review, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"pattern review rejected: {exc}", file=sys.stderr)
        return 1
    print(f"PATTERN REVIEW: {review['review_status']} ({len(review['candidate_patterns'])} candidate(s))")
    print(f"Source: {review['source']['name']} · inventory sha256:{review['provenance']['inventory_sha256']}")
    print("No LLM called; no code executed; synthesis/execution remain unauthorized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
