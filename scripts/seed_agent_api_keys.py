"""
Phase 10E — Generate unique per-agent API keys.

Generates one hc_-prefixed key per internal service, writes the raw to
secrets/agent_api_key_<name>.txt (chmod 600), and emits an SQL UPSERT batch
to stdout so it can be piped into postgres.

Usage:
    python scripts/seed_agent_api_keys.py > /tmp/agent_keys.sql
    docker exec -i postgres psql -U postgres -d hypercode < /tmp/agent_keys.sql
"""
from __future__ import annotations

import hashlib
import os
import secrets
import sys
from pathlib import Path

SERVICES: list[tuple[str, int]] = [
    ("coder-agent",              200),
    ("broski-pets-bridge",       200),
    ("project-strategist",       200),
    ("frontend-specialist",      200),
    ("backend-specialist",       200),
    ("database-architect",       200),
    ("qa-engineer",              200),
    ("devops-engineer",          200),
    ("super-hyper-broski-agent", 500),
    ("security-engineer",        200),
    ("system-architect",         200),
    ("test-agent",               200),
    ("throttle-agent",           1000),
    ("tips-tricks-writer",       200),
]


def generate_agent_key() -> str:
    return "hc_" + secrets.token_urlsafe(32)


def hash_agent_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    secrets_dir = repo_root / "secrets"
    secrets_dir.mkdir(exist_ok=True)

    sql_values: list[str] = []

    for agent_name, rpm in SERVICES:
        raw = generate_agent_key()
        digest = hash_agent_key(raw)
        prefix = raw[:10]

        out_file = secrets_dir / f"agent_api_key_{agent_name}.txt"
        out_file.write_text(raw, encoding="utf-8")
        try:
            os.chmod(out_file, 0o600)
        except OSError:
            pass

        safe_name = agent_name.replace("'", "''")
        sql_values.append(
            f"('{safe_name}', '{prefix}', '{digest}', {rpm}, true)"
        )
        print(f"-- wrote {out_file.relative_to(repo_root)}", file=sys.stderr)

    print("BEGIN;")
    print(
        "INSERT INTO agent_api_keys "
        "(agent_name, key_prefix, key_hash, rate_limit_rpm, is_active) VALUES"
    )
    print(",\n".join("    " + v for v in sql_values) + "\n"
          "ON CONFLICT (agent_name) DO UPDATE SET\n"
          "    key_prefix     = EXCLUDED.key_prefix,\n"
          "    key_hash       = EXCLUDED.key_hash,\n"
          "    rate_limit_rpm = EXCLUDED.rate_limit_rpm,\n"
          "    is_active      = true;")
    print("COMMIT;")


if __name__ == "__main__":
    main()
