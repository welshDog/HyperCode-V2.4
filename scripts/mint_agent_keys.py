"""
Phase 10E key minting — registers per-agent API keys in agent_api_keys.

Mirrors POST /api/v1/agent-keys exactly (hc_ prefix, SHA-256 hash, upsert),
but runs host-side: writes each raw key into secrets/agent_api_key_<name>.txt
(the Docker-secret convention) and emits the matching UPSERT SQL on stdout —
pipe it into psql:

    python scripts/mint_agent_keys.py | docker exec -i postgres psql -U postgres -d hypercode

Pass the agent name(s) to mint (rotates ONLY those):

    python scripts/mint_agent_keys.py healer-agent | docker exec -i postgres psql -U postgres -d hypercode -v ON_ERROR_STOP=1

⚠️  Rotating EVERY agent at once now needs the explicit `--all` flag (running with no arguments used to do that
silently). Rotation replaces the key file AND the database hash; an agent that reads its key per call (healer,
coder-agent) picks the new file up with no restart, others need a restart/recreate.

Raw keys land ONLY in the gitignored secrets/ dir, never on stdout.
"""
import hashlib
import secrets
import sys
from pathlib import Path

AGENTS = [
    "safety-shepherd",
    "crew-orchestrator",
    "healer-agent",
    "coder-agent",
    "broski-pets-bridge",
    "nemoclaw-agent",
    "project-strategist",
    "frontend-specialist",
    "backend-specialist",
    "database-architect",
    "qa-engineer",
    "devops-engineer",
    "super-hyper-broski-agent",
    "security-engineer",
    "system-architect",
    "test-agent",
    # Running services that had a key FILE (or an overlay entry) but no agent_api_keys row, so core rejected them
    # or their Compose secret could not be created: mint them to create the file + row.
    "governor",
    "throttle-agent",
    "tips-tricks-writer",
]

SECRETS_DIR = Path(__file__).resolve().parent.parent / "secrets"


def main() -> None:
    args = sys.argv[1:]
    if not args:
        raise SystemExit(
            "Refusing to run with no arguments (it used to rotate EVERY agent's key).\n"
            "Name the agent(s) to mint, e.g.:  python scripts/mint_agent_keys.py healer-agent\n"
            "or pass --all to rotate all of them deliberately."
        )
    targets = AGENTS if args == ["--all"] else args
    unknown = [t for t in targets if t not in AGENTS]
    if unknown:
        raise SystemExit(f"Unknown agent(s): {unknown} — add to AGENTS first")
    rows = []
    for name in targets:
        raw = "hc_" + secrets.token_urlsafe(32)
        (SECRETS_DIR / f"agent_api_key_{name}.txt").write_text(raw, encoding="ascii")
        rows.append((name, raw[:10], hashlib.sha256(raw.encode()).hexdigest()))

    print("BEGIN;")
    for name, prefix, key_hash in rows:
        print(
            "INSERT INTO agent_api_keys (agent_name, key_prefix, key_hash, rate_limit_rpm, is_active) "
            f"VALUES ('{name}', '{prefix}', '{key_hash}', 200, true) "
            "ON CONFLICT (agent_name) DO UPDATE SET "
            "key_prefix = EXCLUDED.key_prefix, key_hash = EXCLUDED.key_hash, "
            "rate_limit_rpm = EXCLUDED.rate_limit_rpm, is_active = true;"
        )
    print("COMMIT;")


if __name__ == "__main__":
    main()
