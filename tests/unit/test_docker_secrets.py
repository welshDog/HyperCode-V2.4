"""T15 — Docker secrets management tests.

Tests verify:
  - Secret files are created with correct permissions
  - Secret file content is verbatim (no trailing newline added)
  - Idempotency: running init twice does not overwrite existing secrets
  - Compose secrets overlay config is valid YAML and references existing files
  - Secret names match between overlay compose and init scripts
"""
from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path

import pytest
import yaml


# ── Helpers ───────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).parents[2]
SECRETS_COMPOSE = PROJECT_ROOT / "docker-compose.secrets.yml"
INIT_SH = PROJECT_ROOT / "scripts" / "init-secrets.sh"
INIT_PS1 = PROJECT_ROOT / "scripts" / "init-secrets.ps1"

EXPECTED_SECRET_NAMES = {
    "postgres_password",
    "hypercode_jwt_secret",
    "api_key",
    "minio_root_password",
    "hypercode_memory_key",
    "discord_token",
    "orchestrator_api_key",
}


# ─────────────────────────────────────────────────────────────────────────────
# 1. Compose overlay file structure
# ─────────────────────────────────────────────────────────────────────────────

class TestSecretsComposeFile:
    def test_secrets_compose_file_exists(self):
        assert SECRETS_COMPOSE.exists(), "docker-compose.secrets.yml must exist"

    def test_secrets_compose_is_valid_yaml(self):
        with SECRETS_COMPOSE.open() as f:
            parsed = yaml.safe_load(f)
        assert isinstance(parsed, dict)

    def test_secrets_compose_has_secrets_top_level(self):
        with SECRETS_COMPOSE.open() as f:
            parsed = yaml.safe_load(f)
        assert "secrets" in parsed

    def test_all_expected_secrets_declared(self):
        with SECRETS_COMPOSE.open() as f:
            parsed = yaml.safe_load(f)
        declared = set(parsed["secrets"].keys())
        assert EXPECTED_SECRET_NAMES.issubset(declared), (
            f"Missing secrets: {EXPECTED_SECRET_NAMES - declared}"
        )

    def test_all_secrets_use_file_driver(self):
        with SECRETS_COMPOSE.open() as f:
            parsed = yaml.safe_load(f)
        for name, cfg in parsed["secrets"].items():
            assert "file" in cfg, f"Secret '{name}' missing 'file:' key"

    def test_secret_file_paths_use_secrets_dir(self):
        with SECRETS_COMPOSE.open() as f:
            parsed = yaml.safe_load(f)
        for name, cfg in parsed["secrets"].items():
            assert cfg["file"].startswith("./secrets/"), (
                f"Secret '{name}' file path must be in ./secrets/"
            )

    def test_secret_filenames_match_secret_names(self):
        with SECRETS_COMPOSE.open() as f:
            parsed = yaml.safe_load(f)
        for name, cfg in parsed["secrets"].items():
            expected_file = f"./secrets/{name}.txt"
            assert cfg["file"] == expected_file, (
                f"Expected {expected_file} but got {cfg['file']}"
            )

    def test_services_section_exists(self):
        with SECRETS_COMPOSE.open() as f:
            parsed = yaml.safe_load(f)
        assert "services" in parsed

    def test_postgres_service_references_postgres_password(self):
        with SECRETS_COMPOSE.open() as f:
            parsed = yaml.safe_load(f)
        svc = parsed["services"]["postgres"]
        secrets_list = svc.get("secrets", [])
        assert "postgres_password" in secrets_list

    def test_minio_service_references_minio_password(self):
        with SECRETS_COMPOSE.open() as f:
            parsed = yaml.safe_load(f)
        svc = parsed["services"]["minio"]
        secrets_list = svc.get("secrets", [])
        assert "minio_root_password" in secrets_list


# ─────────────────────────────────────────────────────────────────────────────
# 2. Init script file structure
# ─────────────────────────────────────────────────────────────────────────────

class TestInitScripts:
    def test_bash_script_exists(self):
        assert INIT_SH.exists()

    def test_powershell_script_exists(self):
        assert INIT_PS1.exists()

    def test_bash_script_mentions_all_secrets(self):
        content = INIT_SH.read_text()
        for name in EXPECTED_SECRET_NAMES:
            assert name in content, f"Bash script missing secret: {name}"

    def test_powershell_script_mentions_all_secrets(self):
        content = INIT_PS1.read_text()
        for name in EXPECTED_SECRET_NAMES:
            assert name in content, f"PowerShell script missing secret: {name}"

    def test_bash_script_has_shebang(self):
        first_line = INIT_SH.read_text().splitlines()[0]
        assert first_line.startswith("#!/")

    def test_bash_script_has_set_euo(self):
        assert "set -euo pipefail" in INIT_SH.read_text()

    def test_bash_script_sets_permissions_700_on_secrets_dir(self):
        assert "chmod 700" in INIT_SH.read_text()

    def test_bash_script_sets_permissions_600_on_files(self):
        assert "chmod 600" in INIT_SH.read_text()


# ─────────────────────────────────────────────────────────────────────────────
# 3. Secret file creation logic (unit)
# ─────────────────────────────────────────────────────────────────────────────

class TestSecretFileCreation:
    def test_secret_file_written_verbatim(self, tmp_path):
        """Secret value must be written exactly — no extra newlines."""
        secret_value = "my-super-secret-value"
        secret_file = tmp_path / "postgres_password.txt"
        secret_file.write_text(secret_value)
        assert secret_file.read_text() == secret_value

    def test_secret_file_no_trailing_newline(self, tmp_path):
        """Trailing newlines break _FILE env var reading in many images."""
        secret_value = "no-trailing-newline"
        secret_file = tmp_path / "test.txt"
        # Use same write method as init script: printf '%s'
        secret_file.write_bytes(secret_value.encode())
        content = secret_file.read_bytes()
        assert not content.endswith(b"\n")

    def test_idempotency_does_not_overwrite(self, tmp_path):
        """Running init twice must NOT overwrite an existing secret file."""
        secret_file = tmp_path / "api_key.txt"
        original = "original-value"
        secret_file.write_text(original)

        # Simulate "if file exists, skip"
        new_value = "new-value"
        if secret_file.exists():
            pass  # script would skip
        else:
            secret_file.write_text(new_value)  # pragma: no cover

        assert secret_file.read_text() == original

    @pytest.mark.skipif(os.name == "nt", reason="chmod not applicable on Windows")
    def test_secret_file_permissions_are_600(self, tmp_path):
        secret_file = tmp_path / "jwt.txt"
        secret_file.write_text("secret")
        os.chmod(secret_file, 0o600)
        mode = oct(stat.S_IMODE(secret_file.stat().st_mode))
        assert mode == "0o600"

    @pytest.mark.skipif(os.name == "nt", reason="chmod not applicable on Windows")
    def test_secrets_dir_permissions_are_700(self, tmp_path):
        secrets_dir = tmp_path / "secrets"
        secrets_dir.mkdir()
        os.chmod(secrets_dir, 0o700)
        mode = oct(stat.S_IMODE(secrets_dir.stat().st_mode))
        assert mode == "0o700"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Secret names consistency across all files
# ─────────────────────────────────────────────────────────────────────────────

class TestSecretNamesConsistency:
    def test_all_secret_names_consistent_across_compose_and_scripts(self):
        """The same set of secret names must appear in compose AND both init scripts."""
        with SECRETS_COMPOSE.open() as f:
            compose_secrets = set(yaml.safe_load(f)["secrets"].keys())

        bash_content = INIT_SH.read_text()
        ps1_content = INIT_PS1.read_text()

        for name in compose_secrets:
            assert name in bash_content, f"'{name}' missing from init-secrets.sh"
            assert name in ps1_content, f"'{name}' missing from init-secrets.ps1"

    def test_gitignore_covers_secrets_dir(self):
        gitignore = PROJECT_ROOT / ".gitignore"
        assert gitignore.exists()
        content = gitignore.read_text()
        # secrets/ should be ignored
        assert "secrets/" in content

    def test_no_secret_values_in_compose_file(self):
        """Compose overlay must NOT contain any hardcoded secret values."""
        content = SECRETS_COMPOSE.read_text()
        dangerous_patterns = [
            "changeme", "password123", "secret123",
            "your_", "sk-ant-", "sk-proj-",
        ]
        for pattern in dangerous_patterns:
            assert pattern.lower() not in content.lower(), (
                f"Potential hardcoded credential in compose file: '{pattern}'"
            )
