from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "architecture_inventory.py"
spec = importlib.util.spec_from_file_location("architecture_inventory", SCRIPT)
assert spec and spec.loader
inventory_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory_module)


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "sample-repo"
    (root / "backend").mkdir(parents=True)
    (root / ".git").mkdir()
    (root / "node_modules" / "unsafe-package").mkdir(parents=True)
    (root / "docker-compose.yml").write_text(
        "services:\n"
        "  api:\n"
        "    build:\n"
        "      context: ./backend\n"
        "      dockerfile: Dockerfile\n"
        "    ports: ['127.0.0.1:8090:8080']\n"
        "    depends_on: [redis]\n"
        "  redis:\n"
        "    image: redis:8-alpine\n",
        encoding="utf-8",
    )
    (root / "backend" / "Dockerfile").write_text(
        "FROM python:3.12-slim AS runtime\nUSER appuser\nEXPOSE 8080\nHEALTHCHECK CMD python -c pass\n",
        encoding="utf-8",
    )
    (root / "package.json").write_text(
        json.dumps({"name": "safe-demo", "packageManager": "npm@x", "dependencies": {"react": "*"}, "scripts": {"test": "test"}}),
        encoding="utf-8",
    )
    (root / "requirements.txt").write_text("fastapi==0.1\nuvicorn>=0.1\n", encoding="utf-8")
    (root / ".env").write_text("SECRET_VALUE=do-not-export-this\n", encoding="utf-8")
    (root / "service_token.json").write_text('{"token":"do-not-export-this"}', encoding="utf-8")
    (root / ".git" / "config").write_text("should-not-be-seen", encoding="utf-8")
    (root / "node_modules" / "unsafe-package" / "package.json").write_text("{}", encoding="utf-8")
    return root


def test_inventory_is_local_bounded_and_secret_redacted(tmp_path):
    root = _repo(tmp_path)
    result = inventory_module.build_inventory(root)
    serialized = json.dumps(result)

    assert result["schema_version"] == 1
    assert result["scan_limits"]["inventory_complete"] is True
    assert result["source"] == {"kind": "local-directory", "name": "sample-repo", "root_label": "."}
    assert result["safety"] == {
        "repository_cloned": False,
        "code_executed": False,
        "llm_called": False,
        "secret_values_exported": False,
        "raw_source_exported": False,
    }
    assert "SECRET_VALUE" not in serialized
    assert "do-not-export-this" not in serialized
    assert ".env" not in result["files"]
    assert "service_token.json" not in result["files"]
    assert not any(".git" in path or "node_modules" in path for path in result["files"])

    compose = next(item for item in result["manifests"] if item["kind"] == "compose")
    assert [service["name"] for service in compose["metadata"]["services"]] == ["api", "redis"]
    api = compose["metadata"]["services"][0]
    assert api["build"] == {"context": "./backend", "dockerfile": "Dockerfile"}
    assert api["ports"] == ["127.0.0.1:8090:8080"]
    assert result["safety"]["secret_values_exported"] is False
    assert api["depends_on"] == ["redis"]

    dockerfile = next(item for item in result["manifests"] if item["kind"] == "dockerfile")
    assert dockerfile["metadata"]["base_stages"] == [{"image": "python:3.12-slim", "stage": "runtime"}]
    assert dockerfile["metadata"]["users"] == ["appuser"]

    node = next(item for item in result["manifests"] if item["kind"] == "node")
    assert node["metadata"]["name"] == "safe-demo"
    assert node["metadata"]["dependency_names"] == ["react"]
    python_manifest = next(item for item in result["manifests"] if item["kind"] == "python")
    assert python_manifest["metadata"]["dependency_names"] == ["fastapi", "uvicorn"]


def test_inventory_hashes_are_deterministic_and_do_not_fingerprint_raw_values(tmp_path):
    root = _repo(tmp_path)
    first = inventory_module.build_inventory(root)
    second = inventory_module.build_inventory(root)
    assert first == second
    assert all(len(item["sha256"]) == 64 for item in first["manifests"])
    compose = root / "docker-compose.yml"
    before = next(item["sha256"] for item in first["manifests"] if item["path"] == "docker-compose.yml")
    compose.write_text(compose.read_text(encoding="utf-8").replace("127.0.0.1:8090:8080", "127.0.0.1:8091:8080"), encoding="utf-8")
    after_inventory = inventory_module.build_inventory(root)
    after = next(item["sha256"] for item in after_inventory["manifests"] if item["path"] == "docker-compose.yml")
    assert before != after


def test_compose_interpolation_and_url_credentials_are_redacted(tmp_path):
    root = _repo(tmp_path)
    compose = root / "docker-compose.yml"
    compose.write_text(
        "services:\\n  api:\\n    image: internal:${IMAGE_TAG:-latest}\\n    environment:\\n      DATABASE_URL: postgresql://user:[REDACTED]@example.invalid/db\\n    ports: ['${HOST_IP}:9090:8080']\\n",
        encoding="utf-8",
    )
    result = inventory_module.build_inventory(root)
    rendered = json.dumps(result)
    assert "password@example.invalid" not in rendered
    assert "${IMAGE_TAG" not in rendered
    assert "${HOST_IP}" not in rendered


def test_compose_safe_loader_handles_docker_compose_custom_tags(tmp_path):
    root = _repo(tmp_path)
    (root / "docker-compose.override.yml").write_text(
        "services:\n  api:\n    security_opt: !override\n      - no-new-privileges:true\n    environment:\n      API_KEY: ${API_KEY:-redacted}\n",
        encoding="utf-8",
    )
    result = inventory_module.build_inventory(root)
    overlay = next(item for item in result["manifests"] if item["path"] == "docker-compose.override.yml")
    assert overlay["metadata"]["services"][0]["environment_names"] == ["API_KEY"]
    assert "${API_KEY" not in json.dumps(result)
    assert inventory_module.build_inventory(root) == result



def test_inventory_enforces_file_count_limit(tmp_path):
    root = _repo(tmp_path)
    for index in range(8):
        (root / f"Dockerfile.{index}").write_text("FROM scratch\n", encoding="utf-8")
    result = inventory_module.build_inventory(root, max_files=3)
    assert result["scan_limits"]["visited_files"] <= 3
    assert result["scan_limits"]["included_manifests"] <= 3
    assert result["scan_limits"]["inventory_complete"] is False


def test_inventory_never_follows_symlinked_directories(tmp_path):
    root = _repo(tmp_path)
    outside = tmp_path / "external"
    outside.mkdir()
    (outside / "Dockerfile.external").write_text("FROM private/image\n", encoding="utf-8")
    link = root / "external-link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        import pytest
        pytest.skip("directory symlinks unavailable")
    result = inventory_module.build_inventory(root)
    assert not any(path.startswith("external-link/") for path in result["files"])
