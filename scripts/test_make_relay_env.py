"""Tests for scripts/make_relay_env.py (fake data only; never touches a real .env)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import make_relay_env as m  # noqa: E402

FAKE = """# pets env
SEPOLIA_RPC=https://rpc.example/fake
CONTRACT_ADDRESS=0xFAKE
DEPLOYER_KEY=fake-deployer
PINATA_JWT=fake.jwt.value
REDIS_HOST=redis
REDIS_PASSWORD="quoted pw"
IPFS_GATEWAY=https://gw.example/ipfs
CDP_API_KEY_SECRET=must-not-leak
GITHUB_TOKEN=must-not-leak
SUPABASE_SERVICE_ROLE_KEY=must-not-leak
ANTHROPIC_API_KEY=must-not-leak
AGENT_KEY=must-not-leak
GROQ_API_KEY=must-not-leak
"""


def test_only_the_allowlisted_variables_survive_and_nothing_else_leaks():
    kept, names, dropped = m.pick_lines(FAKE)
    blob = "\n".join(kept)
    assert "must-not-leak" not in blob
    for secret in ("CDP_API_KEY_SECRET", "GITHUB_TOKEN", "SUPABASE_SERVICE_ROLE_KEY", "ANTHROPIC_API_KEY", "AGENT_KEY", "GROQ_API_KEY"):
        assert secret not in blob
    assert set(names) == {"SEPOLIA_RPC", "CONTRACT_ADDRESS", "DEPLOYER_KEY", "PINATA_JWT", "REDIS_HOST", "REDIS_PASSWORD", "IPFS_GATEWAY"}
    assert dropped == 6


def test_kept_lines_are_copied_byte_for_byte_including_quotes():
    kept, _, _ = m.pick_lines(FAKE)
    assert 'REDIS_PASSWORD="quoted pw"' in kept and "SEPOLIA_RPC=https://rpc.example/fake" in kept


def test_the_last_assignment_of_a_name_wins_like_dotenv():
    kept, _, _ = m.pick_lines("PINATA_JWT=old\nPINATA_JWT=new\n")
    assert kept == ["PINATA_JWT=new"]


def test_comments_blank_lines_and_export_prefix():
    kept, names, _ = m.pick_lines("# SEPOLIA_RPC=commented\n\nexport DEPLOYER_KEY=x\n")
    assert names == ["DEPLOYER_KEY"] and kept == ["export DEPLOYER_KEY=x"]


def test_a_name_that_merely_contains_an_allowed_name_is_not_kept():
    kept, names, dropped = m.pick_lines("PINATA_JWT_OLD=x\nMY_SEPOLIA_RPC=x\nREDIS_HOSTNAME=x\n")
    assert kept == [] and names == [] and dropped == 3


def test_the_required_set_is_exactly_what_the_relay_code_requires():
    assert set(m.REQUIRED) == {"SEPOLIA_RPC", "CONTRACT_ADDRESS", "DEPLOYER_KEY", "PINATA_JWT"}
    assert set(m.OPTIONAL).isdisjoint(m.REQUIRED)


@pytest.fixture
def box(tmp_path, monkeypatch):
    pets = tmp_path / "pets"
    pets.mkdir()
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    monkeypatch.setenv("BROSKIPETS_DIR", str(pets))
    monkeypatch.setattr(sys, "argv", ["make_relay_env.py"])
    return pets, work


def test_dry_run_writes_nothing_and_prints_no_values(box, capsys):
    pets, work = box
    (pets / ".env").write_text(FAKE, encoding="utf-8")
    assert m.main() == 0
    out = capsys.readouterr().out
    assert not (work / "secrets" / "evolve_relay.env").exists()
    assert "fake-deployer" not in out and "must-not-leak" not in out and "fake.jwt.value" not in out


def test_write_creates_the_minimal_file_and_prints_no_values(box, capsys, monkeypatch):
    pets, work = box
    (pets / ".env").write_text(FAKE, encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["make_relay_env.py", "--write"])
    assert m.main() == 0
    out = capsys.readouterr().out
    text = (work / "secrets" / "evolve_relay.env").read_text(encoding="utf-8")
    assert "DEPLOYER_KEY=fake-deployer" in text and "must-not-leak" not in text
    assert "fake-deployer" not in out and "must-not-leak" not in out


def test_a_missing_required_variable_aborts_and_writes_nothing(box, capsys, monkeypatch):
    pets, work = box
    (pets / ".env").write_text(FAKE.replace("PINATA_JWT=fake.jwt.value\n", ""), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["make_relay_env.py", "--write"])
    assert m.main() == 2
    assert "PINATA_JWT" in capsys.readouterr().out and not (work / "secrets" / "evolve_relay.env").exists()


def test_a_missing_source_file_aborts(box, capsys):
    assert m.main() == 2 and "missing source env file" in capsys.readouterr().out
