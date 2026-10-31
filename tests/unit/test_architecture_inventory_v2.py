"""Schema 2 inventory: verifiable content hashes, compose hardening flags, Python module signals."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("architecture_inventory_v2", ROOT / "scripts" / "architecture_inventory.py")
assert spec and spec.loader
inv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inv)


def _manifest(result, path):
    return next(item for item in result["manifests"] if item["path"] == path)


def _write(root: Path, rel: str, text: str, *, newline: str = "\n") -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.replace("\n", newline).encode("utf-8"))
    return path


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------- fix 1: evidence hashes a reviewer can check ----------

def test_manifest_has_separate_metadata_and_content_hashes_and_no_legacy_field(tmp_path):
    _write(tmp_path, "requirements.txt", "fastapi>=1\nuvicorn\n")
    entry = _manifest(inv.build_inventory(tmp_path), "requirements.txt")
    assert "sha256" not in entry
    assert len(entry["metadata_sha256"]) == 64
    assert entry["content_sha256"] == _sha("fastapi>=1\nuvicorn\n")
    assert entry["content_sha256"] != entry["metadata_sha256"]
    assert "content_sha256_withheld" not in entry


def test_content_hash_is_the_same_for_crlf_and_lf_checkouts(tmp_path):
    text = "FROM python:3.12-slim\nUSER app\n"
    lf = tmp_path / "lf"
    crlf = tmp_path / "crlf"
    _write(lf, "Dockerfile", text)
    _write(crlf, "Dockerfile", text, newline="\r\n")
    a = _manifest(inv.build_inventory(lf), "Dockerfile")["content_sha256"]
    b = _manifest(inv.build_inventory(crlf), "Dockerfile")["content_sha256"]
    assert a == b == _sha(text)


def test_editing_a_file_changes_its_content_hash_even_when_metadata_does_not(tmp_path):
    _write(tmp_path, "Dockerfile", "FROM python:3.12\nRUN echo one\n")
    before = _manifest(inv.build_inventory(tmp_path), "Dockerfile")
    _write(tmp_path, "Dockerfile", "FROM python:3.12\nRUN echo two\n")
    after = _manifest(inv.build_inventory(tmp_path), "Dockerfile")
    assert before["metadata_sha256"] == after["metadata_sha256"]
    assert before["content_sha256"] != after["content_sha256"]


def test_content_hash_is_withheld_for_secret_bearing_files(tmp_path):
    _write(tmp_path, "docker-compose.yml", "services:\n  db:\n    image: postgres\n    environment:\n      POSTGRES_PASSWORD: hunter2hunter2\n")
    _write(tmp_path, "Dockerfile", "FROM python:3.12\nENV REGISTRY=https://user:pa55word@example.invalid/x\n")
    result = inv.build_inventory(tmp_path)
    for path in ("docker-compose.yml", "Dockerfile"):
        entry = _manifest(result, path)
        assert entry["content_sha256"] is None
        assert entry["content_sha256_withheld"] == "secret-like-content"
    rendered = json.dumps(result)
    assert "hunter2hunter2" not in rendered and "pa55word" not in rendered


def test_interpolations_file_keys_and_redaction_markers_do_not_withhold_the_hash(tmp_path):
    _write(
        tmp_path,
        "docker-compose.yml",
        "services:\n  api:\n    image: app\n    environment:\n"
        "      API_KEY: ${API_KEY:-redacted}\n"
        "      JWT_SECRET_FILE: /run/secrets/jwt_secret\n"
        "      DB_PASSWORD: \"[REDACTED]\"\n",
    )
    entry = _manifest(inv.build_inventory(tmp_path), "docker-compose.yml")
    assert entry["content_sha256"] is not None


def test_non_utf8_manifest_has_no_content_hash(tmp_path):
    (tmp_path / "Dockerfile").write_bytes(b"FROM scratch\n\xff\xfe\n")
    entry = _manifest(inv.build_inventory(tmp_path), "Dockerfile")
    assert entry["kind"] == "binary-or-non-utf8"
    assert entry["content_sha256"] is None
    assert entry["content_sha256_withheld"] == "non-utf8"


# ---------- fix 2: compose hardening and capability signals ----------

COMPOSE = """services:
  tight:
    image: app
    read_only: true
    cap_drop: [ALL]
    cap_add: [net_bind_service]
    security_opt:
      - no-new-privileges:true
    secrets: [jwt_secret, {source: api_key}]
    environment:
      DOCKER_HOST: tcp://proxy:2375
  loose:
    image: app
    privileged: true
    network_mode: host
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
  plain:
    image: app
"""


def test_compose_hardening_and_capability_flags_are_booleans_and_names_only(tmp_path):
    _write(tmp_path, "docker-compose.yml", COMPOSE)
    result = inv.build_inventory(tmp_path)
    services = {s["name"]: s for s in _manifest(result, "docker-compose.yml")["metadata"]["services"]}
    tight, loose, plain = services["tight"], services["loose"], services["plain"]
    assert tight["read_only"] is True and tight["cap_drop"] == ["ALL"] and tight["cap_add"] == ["NET_BIND_SERVICE"]
    assert tight["no_new_privileges"] is True and tight["docker_host_env"] is True
    assert tight["secret_names"] == ["api_key", "jwt_secret"]
    assert loose["privileged"] is True and loose["host_network"] is True and loose["docker_socket_mounted"] is True
    assert plain["read_only"] is False and plain["cap_drop"] == [] and plain["no_new_privileges"] is False
    assert plain["docker_socket_mounted"] is False and plain["privileged"] is False
    rendered = json.dumps(result)
    assert "/var/run/docker.sock" not in rendered  # the mount path itself is never exported
    assert "tcp://proxy:2375" not in rendered  # nor environment values


def test_no_new_privileges_false_is_not_counted(tmp_path):
    _write(tmp_path, "docker-compose.yml", "services:\n  a:\n    image: x\n    security_opt: ['no-new-privileges:false']\n")
    service = _manifest(inv.build_inventory(tmp_path), "docker-compose.yml")["metadata"]["services"][0]
    assert service["no_new_privileges"] is False


# ---------- fix 2: Python module signals ----------

MODULE = '''
import subprocess
import httpx
from cryptography.hazmat.primitives import hashes
import json, os

API_TOKEN = "super-secret-literal-value"

@app.get("/health")
async def health(): ...

@router.post("/v1/things/{thing_id}")
def create(thing_id): ...

@app.get(some_variable)
def dynamic(): ...

@app.get("not-a-path with spaces")
def junk(): ...

def run():
    eval("1")
    os.system("ls")
'''


def test_python_module_routes_and_sensitive_imports_are_extracted_without_source_text(tmp_path):
    _write(tmp_path, "main.py", MODULE)
    result = inv.build_inventory(tmp_path)
    entry = _manifest(result, "main.py")
    assert entry["kind"] == "python-module"
    assert entry["metadata"]["routes"] == [{"method": "GET", "path": "/health"}, {"method": "POST", "path": "/v1/things/{thing_id}"}]
    assert entry["metadata"]["sensitive_imports"] == ["crypto:cryptography", "network-client:httpx", "process-exec:subprocess"]
    assert entry["metadata"]["dynamic_eval"] is True and entry["metadata"]["process_exec_calls"] is True
    rendered = json.dumps(result)
    assert "super-secret-literal-value" not in rendered
    assert "not-a-path" not in rendered
    assert entry["content_sha256"] is None and entry["content_sha256_withheld"] == "secret-like-content"


def test_quiet_module_is_clean_and_python_calls_do_not_trip_the_secret_check(tmp_path):
    _write(tmp_path, "keys.py", "import json\n\ndef load(token: str, secret=None):\n    token = build(token)\n    return token\n")
    entry = _manifest(inv.build_inventory(tmp_path), "keys.py")
    assert entry["metadata"] == {"routes": [], "sensitive_imports": [], "dynamic_eval": False, "process_exec_calls": False}
    assert entry["content_sha256"] is not None


def test_modules_deeper_than_one_level_tests_and_secret_named_files_are_not_scanned(tmp_path):
    for rel in ("top.py", "pkg/mid.py", "pkg/deep/too_deep.py", "tests/helper.py", "test_thing.py", "conftest.py", "secrets.py", "pkg/tests/x.py"):
        _write(tmp_path, rel, "x = 1\n")
    scanned = {item["path"] for item in inv.build_inventory(tmp_path)["manifests"] if item["kind"] == "python-module"}
    assert scanned == {"top.py", "pkg/mid.py"}


def test_syntax_error_is_recorded_not_raised(tmp_path):
    _write(tmp_path, "broken.py", "def (:\n")
    entry = _manifest(inv.build_inventory(tmp_path), "broken.py")
    assert entry["metadata"] == {"parse_error": "SyntaxError"}


def test_module_cap_is_best_effort_and_never_makes_the_inventory_incomplete(tmp_path, monkeypatch):
    monkeypatch.setattr(inv, "MAX_PYTHON_MODULES", 3)
    _write(tmp_path, "Dockerfile", "FROM scratch\n")
    for index in range(7):
        _write(tmp_path, f"mod{index}.py", "x = 1\n")
    limits = inv.build_inventory(tmp_path)["scan_limits"]
    assert limits["python_modules_scanned"] == 3
    assert limits["python_modules_skipped"] == 4
    assert limits["inventory_complete"] is True


def test_oversized_module_is_skipped_without_failing(tmp_path):
    _write(tmp_path, "big.py", "x = 1\n" + "# pad\n" * (inv.MAX_MANIFEST_BYTES // 6 + 10))
    _write(tmp_path, "small.py", "x = 1\n")
    result = inv.build_inventory(tmp_path)
    assert [m["path"] for m in result["manifests"] if m["kind"] == "python-module"] == ["small.py"]
    assert result["scan_limits"]["python_modules_skipped"] == 1
    assert result["scan_limits"]["inventory_complete"] is True


def test_inventory_with_python_modules_is_deterministic(tmp_path):
    _write(tmp_path, "main.py", MODULE)
    _write(tmp_path, "docker-compose.yml", COMPOSE)
    assert inv.build_inventory(tmp_path) == inv.build_inventory(tmp_path)
