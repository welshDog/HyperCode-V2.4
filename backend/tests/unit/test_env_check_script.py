import os
import subprocess
from pathlib import Path

import pytest


def _run_env_check(repo_root: Path, args: list[str], env: dict[str, str] | None = None):
    script = repo_root / "scripts" / "env_check.py"
    if not script.exists():
        pytest.skip("env_check.py not found")

    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    proc = subprocess.run(
        [os.sys.executable, str(script), *args],
        cwd=str(repo_root),
        env=full_env,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout + proc.stderr


def test_fails_when_root_env_missing(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[3]
    fake_root = tmp_path / "root"
    fake_root.mkdir()

    (fake_root / "docker-compose.yml").write_text(
        "services:\n  app:\n    environment:\n      - API_KEY=${API_KEY}\n",
        encoding="utf-8",
    )

    code, out = _run_env_check(repo_root, ["--root", str(fake_root), "--files", "docker-compose.yml"])
    assert code != 0
    assert "missing_root_env" in out


def test_reports_duplicate_keys_as_warning(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[3]
    fake_root = tmp_path / "root"
    fake_root.mkdir()

    (fake_root / ".env").write_text("FOO=1\nFOO=2\n", encoding="utf-8")
    (fake_root / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")

    code, out = _run_env_check(repo_root, ["--root", str(fake_root), "--files", "docker-compose.yml"])
    assert code == 0
    assert "duplicate_key:FOO" in out


def test_missing_required_compose_var_is_error(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[3]
    fake_root = tmp_path / "root"
    fake_root.mkdir()

    (fake_root / ".env").write_text("PRESENT=1\n", encoding="utf-8")
    (fake_root / "docker-compose.yml").write_text(
        "services:\n  app:\n    environment:\n      - NEED=${NEED}\n      - OK=${PRESENT:-x}\n",
        encoding="utf-8",
    )

    code, out = _run_env_check(repo_root, ["--root", str(fake_root), "--files", "docker-compose.yml"])
    assert code != 0
    assert "missing_required_env_var:NEED" in out


def test_secrets_file_missing_is_error(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[3]
    fake_root = tmp_path / "root"
    fake_root.mkdir()

    (fake_root / ".env").write_text("X=1\n", encoding="utf-8")
    (fake_root / "docker-compose.yml").write_text("services: {}\n", encoding="utf-8")
    (fake_root / "docker-compose.secrets.yml").write_text(
        "secrets:\n  api_key:\n    file: ./secrets/api_key.txt\n",
        encoding="utf-8",
    )

    code, out = _run_env_check(
        repo_root,
        ["--root", str(fake_root), "--files", "docker-compose.yml", "docker-compose.secrets.yml"],
    )
    assert code != 0
    assert "missing_secret_file" in out
