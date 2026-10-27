from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "pattern_review.py"
spec = importlib.util.spec_from_file_location("pattern_review", SCRIPT)
assert spec and spec.loader
review_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review_module)


def _inventory():
    return {
        "schema_version": 1,
        "source": {"kind": "local-directory", "name": "demo-repo", "root_label": "."},
        "safety": {
            "repository_cloned": False,
            "code_executed": False,
            "llm_called": False,
            "secret_values_exported": False,
            "raw_source_exported": False,
        },
        "scan_limits": {"inventory_complete": True},
        "manifests": [
            {
                "path": "docker-compose.yml",
                "kind": "compose",
                "sha256": "a" * 64,
                "metadata": {
                    "services": [
                        {"name": "api", "depends_on": ["redis"], "ports": ["127.0.0.1:8090:8080"]},
                        {"name": "redis", "depends_on": [], "ports": []},
                    ]
                },
            },
            {"path": "Dockerfile", "kind": "dockerfile", "sha256": "b" * 64, "metadata": {"base_stages": [{"image": "python:3.12", "stage": "runtime"}], "users": ["app"], "healthcheck": True}},
            {"path": "requirements.txt", "kind": "python", "sha256": "c" * 64, "metadata": {"dependency_names": ["fastapi"]}},
        ],
    }


def _approval(inventory):
    return {
        "schema_version": review_module.APPROVAL_SCHEMA,
        "approved": True,
        "source_name": inventory["source"]["name"],
        "inventory_sha256": review_module.canonical_digest(inventory),
        "approval_id": "approval-demo-001",
        "approved_by": "human-reviewer",
        "approved_at": "2026-10-21T12:00:00Z",
    }


def test_approval_required_and_exact_inventory_digest_bound():
    inventory = _inventory()
    approval = _approval(inventory)
    approval["approved"] = False
    with pytest.raises(ValueError, match="no explicit human approval"):
        review_module.build_review(inventory, approval)

    approval = _approval(inventory)
    inventory["source"]["name"] = "another-repo"
    with pytest.raises(ValueError, match="source_name does not match"):
        review_module.build_review(inventory, approval)


def test_review_packet_is_provenance_linked_and_pending_human_review():
    inventory = _inventory()
    review = review_module.build_review(inventory, _approval(inventory))
    assert review["review_status"] == "pending_human_review"
    assert review["synthesis_authorized"] is False
    assert review["execution_authorized"] is False
    assert review["provenance"]["inventory_sha256"] == review_module.canonical_digest(inventory)
    assert review["provenance"]["approval_id"] == "approval-demo-001"
    topology = next(pattern for pattern in review["candidate_patterns"] if pattern["candidate_id"] == "compose-service-topology")
    assert topology["facts"]["dependency_edges"] == [{"from": "api", "to": "redis", "source": "docker-compose.yml"}]
    assert topology["evidence"] == [{"path": "docker-compose.yml", "sha256": "a" * 64}]


def test_pattern_candidates_are_deterministic_and_no_raw_text_or_secrets():
    inventory = _inventory()
    approval = _approval(inventory)
    first = review_module.build_review(inventory, approval)
    second = review_module.build_review(inventory, approval)
    first["provenance"].pop("approved_at")
    second["provenance"].pop("approved_at")
    assert first == second
    rendered = json.dumps(first)
    assert "SECRET_VALUE" not in rendered
    assert "source_code" not in rendered
    assert "raw_source" not in rendered


def test_unsafe_inventory_is_rejected():
    inventory = _inventory()
    inventory["safety"]["code_executed"] = True
    with pytest.raises(ValueError, match="safety claims"):
        review_module.build_review(inventory, _approval(inventory))


def test_incomplete_inventory_is_rejected_before_pattern_extraction():
    inventory = _inventory()
    inventory["scan_limits"]["inventory_complete"] = False
    with pytest.raises(ValueError, match="incomplete inventory"):
        review_module.build_review(inventory, _approval(inventory))


def test_traversal_paths_and_raw_source_are_rejected():
    inventory = _inventory()
    inventory["manifests"][0]["path"] = "../outside/compose.yml"
    with pytest.raises(ValueError, match="non-repository manifest path"):
        review_module.build_review(inventory, _approval(inventory))

    inventory = _inventory()
    inventory["manifests"][0]["content"] = "raw repo contents"
    with pytest.raises(ValueError, match="raw source text"):
        review_module.build_review(inventory, _approval(inventory))
