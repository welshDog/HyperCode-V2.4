"""
Phase 10E key minting — registers per-agent API keys in agent_api_keys.

Mirrors POST /api/v1/agent-keys exactly (hc_ prefix, SHA-256 hash, upsert),
but runs host-side: writes each raw key into secrets/agent_api_key_<name>.txt
(the Docker-secret convention) and emits the matching UPSERT SQL on stdout —
pipe it into psql:

    python scripts/mint_agent_keys.py | docker exec -i postgres psql -U postgres -d hypercode

Raw keys land ONLY in the gitignored secrets/ dir, never on stdout.
"""
import hashlib
import secrets
from pathlib import Path

AGENTS = [
    "crew-orchestrator",
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
]

SECRETS_DIR = Path(__file__).resolve().parent.parent / "secrets"


def main() -> None:
    rows = []
    for name in AGENTS:
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
