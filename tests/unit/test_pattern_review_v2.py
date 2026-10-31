"""Pattern review over schema 2 inventories: evidence fields, new candidates, v1 compatibility."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, script: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


review = _load("pattern_review_v2", "pattern_review.py")
inventory_tool = _load("architecture_inventory_for_review", "architecture_inventory.py")


def _approval(inventory):
    return {
        "schema_version": review.APPROVAL_SCHEMA,
        "approved": True,
        "source_name": inventory["source"]["name"],
        "inventory_sha256": review.canonical_digest(inventory),
        "approval_id": "approval-demo-002",
        "approved_by": "human-reviewer",
        "approved_at": "2026-10-31T12:00:00Z",
    }


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "demo-svc"
    root.mkdir()
    (root / "docker-compose.yml").write_text(
        "services:\n  api:\n    image: app\n    read_only: true\n    cap_drop: [ALL]\n"
        "    security_opt: ['no-new-privileges:true']\n    secrets: [jwt]\n"
        "  agent:\n    image: agent\n    volumes: ['/var/run/docker.sock:/var/run/docker.sock']\n    privileged: true\n",
        encoding="utf-8",
    )
    (root / "Dockerfile").write_text("FROM python:3.12 AS build\nFROM python:3.12\nUSER app\nHEALTHCHECK CMD true\n", encoding="utf-8")
    (root / "requirements.txt").write_text("fastapi\nhttpx\n", encoding="utf-8")
    (root / "main.py").write_text(
        "import httpx\nimport subprocess\n\n@app.get('/health')\ndef health(): ...\n\n@app.post('/v1/mint')\ndef mint(): ...\n",
        encoding="utf-8",
    )
    (root / "keys.py").write_text("from cryptography.hazmat.primitives import hashes\n", encoding="utf-8")
    return root


def _packet(tmp_path: Path) -> dict:
    inventory = inventory_tool.build_inventory(_repo(tmp_path))
    return review.build_review(inventory, _approval(inventory))


def _candidate(packet: dict, candidate_id: str) -> dict:
    return next(c for c in packet["candidate_patterns"] if c["candidate_id"] == candidate_id)


def test_full_pipeline_inventory_to_packet_stays_pending_and_unauthorised(tmp_path):
    packet = _packet(tmp_path)
    assert packet["review_status"] == "pending_human_review"
    assert packet["synthesis_authorized"] is False and packet["execution_authorized"] is False
    assert packet["provenance"]["inventory_schema_version"] == 2
    ids = [c["candidate_id"] for c in packet["candidate_patterns"]]
    assert ids == [
        "compose-service-topology", "container-build-hardening-signals", "declared-language-ecosystems",
        "compose-hardening-declarations", "capability-boundary-signals", "python-module-surface",
    ]


def test_evidence_carries_explicit_fingerprints_and_a_legacy_alias_equal_to_the_metadata_hash(tmp_path):
    packet = _packet(tmp_path)
    for candidate in packet["candidate_patterns"]:
        for ref in candidate["evidence"]:
            assert ref["sha256"] == ref["metadata_sha256"]  # alias for older readers, never a file hash
            assert len(ref["metadata_sha256"]) == 64
            assert ref["content_sha256"] is None or len(ref["content_sha256"]) == 64
    docker = _candidate(packet, "container-build-hardening-signals")["evidence"][0]
    raw = (tmp_path / "demo-svc" / "Dockerfile").read_bytes()  # CRLF on Windows checkouts
    real = hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()
    assert docker["content_sha256"] == real  # a reviewer can verify the file


def test_compose_hardening_candidate_lists_declared_options(tmp_path):
    facts = _candidate(_packet(tmp_path), "compose-hardening-declarations")["facts"]
    assert facts["service_count"] == 2
    assert facts["read_only_services"] == ["api"]
    assert facts["cap_drop_all_services"] == ["api"]
    assert facts["no_new_privileges_services"] == ["api"]
    assert facts["services_using_secrets"] == ["api"]


def test_capability_boundary_candidate_reports_risky_capabilities_and_import_categories(tmp_path):
    facts = _candidate(_packet(tmp_path), "capability-boundary-signals")["facts"]
    assert facts["docker_socket_services"] == ["agent"]
    assert facts["privileged_services"] == ["agent"]
    assert facts["host_network_services"] == [] and facts["docker_host_env_services"] == []
    assert facts["python_modules_by_import_category"] == {
        "crypto": ["keys.py"], "network-client": ["main.py"], "process-exec": ["main.py"],
    }
    assert facts["dynamic_eval_modules"] == [] and facts["python_modules_scanned"] == 2


def test_surface_candidate_lists_routes_per_module(tmp_path):
    facts = _candidate(_packet(tmp_path), "python-module-surface")["facts"]
    assert facts["routes_total"] == 2 and facts["modules_with_routes"] == ["main.py"]
    assert facts["routes"] == [
        {"method": "GET", "path": "/health", "module": "main.py"},
        {"method": "POST", "path": "/v1/mint", "module": "main.py"},
    ]
    assert facts["routes_truncated"] is False


def test_new_candidates_stay_inside_the_review_ui_limits(tmp_path):
    inventory = inventory_tool.build_inventory(_repo(tmp_path))
    for index in range(120):  # more compose files than the UI's 80-evidence limit
        inventory["manifests"].append({
            "path": f"docker-compose.{index}.yml", "kind": "compose", "metadata_sha256": "d" * 64, "content_sha256": None,
            "metadata": {"services": [{"name": f"svc{index}", "depends_on": []}]},
        })
    packet = review.build_review(inventory, _approval(inventory))
    for cid in ("compose-hardening-declarations", "capability-boundary-signals"):
        candidate = _candidate(packet, cid)
        assert len(candidate["evidence"]) <= 80
        assert candidate["facts"]["evidence_truncated"] is True


def test_packets_are_deterministic(tmp_path):
    inventory = inventory_tool.build_inventory(_repo(tmp_path))
    approval = _approval(inventory)
    assert review.build_review(inventory, approval) == review.build_review(inventory, approval)


def test_v1_inventory_still_works_and_gets_no_v2_only_candidates():
    inventory = {
        "schema_version": 1,
        "source": {"kind": "local-directory", "name": "old-repo", "root_label": "."},
        "safety": {"repository_cloned": False, "code_executed": False, "llm_called": False, "secret_values_exported": False, "raw_source_exported": False},
        "scan_limits": {"inventory_complete": True},
        "manifests": [{"path": "Dockerfile", "kind": "dockerfile", "sha256": "b" * 64, "metadata": {"base_stages": [{"image": "x", "stage": None}], "users": ["app"], "healthcheck": True}}],
    }
    packet = review.build_review(inventory, _approval(inventory))
    assert [c["candidate_id"] for c in packet["candidate_patterns"]] == ["container-build-hardening-signals"]
    assert packet["candidate_patterns"][0]["evidence"] == [{"path": "Dockerfile", "sha256": "b" * 64}]
    assert packet["provenance"]["inventory_schema_version"] == 1


@pytest.mark.parametrize("mutate,message", [
    (lambda inv: inv.update(schema_version=3), "unsupported inventory schema_version"),
    (lambda inv: inv["manifests"][0].pop("metadata_sha256"), "invalid metadata fingerprint"),
    (lambda inv: inv["manifests"][0].update(metadata_sha256="nothex"), "invalid metadata fingerprint"),
    (lambda inv: inv["manifests"][0].update(content_sha256="nothex"), "invalid content fingerprint"),
    (lambda inv: inv["manifests"][0].update(content="raw file text"), "raw source text"),
])
def test_malformed_v2_inventories_are_rejected(tmp_path, mutate, message):
    inventory = copy.deepcopy(inventory_tool.build_inventory(_repo(tmp_path)))
    mutate(inventory)
    with pytest.raises(ValueError, match=message):
        review.build_review(inventory, _approval(inventory))


def test_approval_is_bound_to_the_new_inventory_digest(tmp_path):
    inventory = inventory_tool.build_inventory(_repo(tmp_path))
    approval = _approval(inventory)
    (tmp_path / "demo-svc" / "main.py").write_text("@app.get('/new')\ndef f(): ...\n", encoding="utf-8")
    changed = inventory_tool.build_inventory(tmp_path / "demo-svc")
    with pytest.raises(ValueError, match="exact inventory digest"):
        review.build_review(changed, approval)  # a stale approval cannot cover changed content


def test_packet_contains_no_secret_values_or_source_text(tmp_path):
    root = _repo(tmp_path)
    (root / "main.py").write_text("API_TOKEN = 'literal-secret-xyz'\n@app.get('/x')\ndef f(): ...\n", encoding="utf-8")
    inventory = inventory_tool.build_inventory(root)
    rendered = json.dumps(review.build_review(inventory, _approval(inventory)))
    assert "literal-secret-xyz" not in rendered
    assert "def f" not in rendered
