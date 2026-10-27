from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / ".github" / "scripts" / "check_dhi_contract.py"
spec = importlib.util.spec_from_file_location("check_dhi_contract", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _fixture(
    tmp_path: Path,
    *,
    builder: str = "dhi.io/python:3.11.18-debian12-dev",
    runtime: str = "dhi.io/python:3.11.18-debian12",
    user: str = "65532:65532",
    healthcheck: str = "DEFAULT",
) -> tuple[Path, Path]:
    context = tmp_path / "service"
    context.mkdir()
    (context / ".dockerignore").write_text(
        ".env\n.env.*\nsecrets/\n*.key\n*.pem\n*.crt\n", encoding="utf-8"
    )
    health = 'CMD ["python", "-c", "import urllib.request; urllib.request.urlopen(\'http://localhost:8090/health\')"]'
    if healthcheck != "DEFAULT":
        health = healthcheck
    dockerfile = f'''FROM {builder} AS builder
RUN python -m venv /app/venv
FROM {runtime} AS runtime
COPY --from=builder --chown=65532:65532 /app/venv /app/venv
USER {user}
HEALTHCHECK --interval=30s {health}
ENTRYPOINT ["python", "/app/entrypoint.py"]
'''
    (context / "Dockerfile").write_text(dockerfile, encoding="utf-8")
    (context / "entrypoint.py").write_text(
        '''import os, subprocess, sys
if sys.argv[1:] == ["api"]:
    subprocess.run(["alembic", "upgrade", "head"], check=True)
    os.execvp("uvicorn", ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090", "--workers", "2"])
if len(sys.argv) < 2:
    raise SystemExit(2)
os.execvp(sys.argv[1], sys.argv[1:])
''',
        encoding="utf-8",
    )
    compose = tmp_path / "compose.yml"
    _write_compose(compose, {"context": "./service", "dockerfile": "Dockerfile"})
    return compose, context


def _write_compose(path: Path, build: dict, **service_overrides) -> None:
    service = {
        "build": build,
        "read_only": True,
        "cap_drop": ["ALL"],
        "security_opt": ["no-new-privileges:true"],
        **service_overrides,
    }
    path.write_text(yaml.safe_dump({"services": {"hyperhealth-api": service}}), encoding="utf-8")


def _check(compose: Path) -> list[str]:
    return module.inspect_service(compose, "hyperhealth-api")


def test_valid_paired_dhi_contract_passes(tmp_path):
    compose, context = _fixture(tmp_path)
    (context / "entrypoint.py").write_text(
        '''import os, subprocess, sys
if sys.argv[1:] == ["api"]:
    subprocess.run(["alembic", "upgrade", "head"], check=True)
    os.execvp("uvicorn", ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8090", "--workers", "2"])
if len(sys.argv) < 2:
    raise SystemExit(2)
os.execvp(sys.argv[1], sys.argv[1:])
''',
        encoding="utf-8",
    )
    assert _check(compose) == []


def test_wrong_builder_base_fails(tmp_path):
    compose, _ = _fixture(tmp_path, builder="python:3.11-slim")
    assert any("builder must use" in item for item in _check(compose))


def test_builder_runtime_version_mismatch_fails(tmp_path):
    compose, _ = _fixture(tmp_path, runtime="dhi.io/python:3.12.2-debian12")
    assert any("must match" in item for item in _check(compose))


def test_root_runtime_user_fails(tmp_path):
    compose, _ = _fixture(tmp_path, user="root")
    assert any("nonroot" in item for item in _check(compose))


def test_shell_healthcheck_binary_fails(tmp_path):
    compose, _ = _fixture(tmp_path, healthcheck="CMD curl -f http://localhost:8090/health")
    assert any("curl/wget" in item for item in _check(compose))


def test_secret_leak_in_build_context_fails(tmp_path):
    compose, context = _fixture(tmp_path)
    (context / ".dockerignore").write_text("__pycache__/\n", encoding="utf-8")
    assert any(".dockerignore must exclude" in item for item in _check(compose))


def test_missing_read_only_hardening_fails(tmp_path):
    compose, _ = _fixture(tmp_path)
    _write_compose(
        compose,
        {"context": "./service", "dockerfile": "Dockerfile"},
        read_only=False,
        cap_drop=[],
        security_opt=[],
    )
    failures = _check(compose)
    assert any("read_only: true" in item for item in failures)
    assert any("drop all capabilities" in item for item in failures)
    assert any("no-new-privileges:true" in item for item in failures)


def test_wrong_service_build_context_is_detected(tmp_path):
    compose, _ = _fixture(tmp_path)
    _write_compose(compose, {"context": "./missing", "dockerfile": "Dockerfile"}, read_only=True, cap_drop=["ALL"], security_opt=["no-new-privileges:true"])
    assert any("build context does not exist" in item for item in _check(compose))


def test_check_gate_also_rejects_startup_wrapper_drift(tmp_path):
    compose, context = _fixture(tmp_path)
    (context / "entrypoint.py").write_text("import sys\\nsys.exit(0)\\n", encoding="utf-8")
    assert any("API entrypoint must migrate" in item for item in _check(compose))


def test_cli_check_mode_passes_and_fails_on_drift(tmp_path):
    compose, _ = _fixture(tmp_path)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--compose", str(compose), "--service", "hyperhealth-api", "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "DHI SOURCE CONTRACT: PASS" in result.stdout

    _write_compose(
        compose,
        {"context": "./service", "dockerfile": "Dockerfile"},
        read_only=False,
        cap_drop=[],
        security_opt=[],
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--compose", str(compose), "--service", "hyperhealth-api", "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "DHI SOURCE CONTRACT: FAIL" in result.stdout
