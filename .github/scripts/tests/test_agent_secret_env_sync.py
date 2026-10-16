"""Drift + guard tests for the vendored read_secret().

1. Every agent file listed in scripts/vendor_secret_env.py TARGETS carries a copy identical to the canonical one.
2. No agent reads an inter-agent / core API key straight from the environment any more - they must go through
   read_secret() (so a *_FILE Compose secret works). Exceptions are explicit, with the reason.

Run: python -m pytest .github/scripts/tests/test_agent_secret_env_sync.py
"""
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts"))
import vendor_secret_env as vend  # noqa: E402

# A raw read of one of these names (os.getenv / os.environ.get / os.environ[...]).
RAW_READ = re.compile(
    r"""(?:os\.getenv|os\.environ\.get|os\.environ\[)\(?\s*['"]"""
    r"""(HYPERCODE_API_KEY|AGENT_API_KEY|API_KEY|CORE_AGENT_KEY)['"]"""
)

# path (relative to agents/) -> reason a raw read is acceptable there
ALLOWED = {
    "coder-studio/main.py": "its _api_key() already reads HYPERCODE_API_KEY_FILE first (file-aware)",
    "base-agent/agent.py": "uses its own file-aware _resolve_secret()",
    "governor/ledger_client.py": "_core_agent_key() reads CORE_AGENT_KEY_FILE first, env is only its fallback",
    "safety-shepherd/safety_shepherd.py": "_core_agent_key() reads CORE_AGENT_KEY_FILE first, env is only its fallback",
    "hyperhealth/seed_checks.py": "operator CLI client run on the host, not a service",
}
SKIP_PARTS = {"node_modules", "tests", ".venv", "venv", "site-packages", "__pycache__"}


def test_vendored_copies_are_identical_to_canonical():
    stale = [rel for rel in vend.TARGETS if vend.process(rel, check=True) != "ok"]
    assert not stale, f"out of sync (run: python scripts/vendor_secret_env.py): {stale}"


def test_helper_is_defined_before_any_module_level_use():
    """meta-research-architect/config.py calls read_secret() at import time; a def placed after it would NameError."""
    import ast

    for rel in vend.TARGETS:
        tree = ast.parse((REPO / "agents" / rel).read_text(encoding="utf-8"))
        defs = [n.lineno for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "read_secret"]
        assert len(defs) == 1, f"{rel}: expected exactly one top-level read_secret def, found {len(defs)}"
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue  # bodies run later, after the module has finished importing
            uses = [n.lineno for n in ast.walk(node) if isinstance(n, ast.Name) and n.id == "read_secret"]
            assert all(u > defs[0] for u in uses), f"{rel}: read_secret used at module level before its def"


def test_no_raw_key_reads_remain_outside_the_allowlist():
    offenders = []
    for py in (REPO / "agents").rglob("*.py"):
        rel = py.relative_to(REPO / "agents").as_posix()
        if SKIP_PARTS & set(py.parts) or py.name.startswith("test_") or rel in ALLOWED:
            continue
        for n, line in enumerate(py.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if RAW_READ.search(line):
                offenders.append(f"{rel}:{n}: {line.strip()}")
    assert not offenders, "raw key reads found - use read_secret():\n" + "\n".join(offenders)


def test_allowlist_entries_still_exist_and_still_need_it():
    """Keep the allow-list honest: an entry that no longer has a raw read should be removed."""
    for rel in ALLOWED:
        p = REPO / "agents" / rel
        assert p.exists(), f"allow-listed file missing: {rel}"
