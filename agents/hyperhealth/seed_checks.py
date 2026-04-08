"""
HyperHealth — Seed Foundational Checks
Registers or updates the 5 core checks in HyperHealth API.

Usage:
    python agents/hyperhealth/seed_checks.py           # create missing only
    python agents/hyperhealth/seed_checks.py --force   # update ALL (safe, no delete)
"""
import httpx
import os
import sys

API_BASE = os.environ.get("HYPERHEALTH_URL", "http://localhost:8095")
API_KEY  = os.environ.get("API_KEY", "")
FORCE    = "--force" in sys.argv


def load_env(path=".env"):
    env = {}
    try:
        for line in open(path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return env


dot_env = load_env()

if not API_KEY:
    API_KEY = dot_env.get("API_KEY", "")
if not API_KEY:
    print("\u274c ERROR: API_KEY not found in env or .env")
    sys.exit(1)


def resolve_db_dsn() -> str:
    dsn = (
        os.environ.get("HYPERCODE_DB_URL")
        or dot_env.get("HYPERCODE_DB_URL")
        or os.environ.get("DATABASE_URL")
        or dot_env.get("DATABASE_URL")
    )
    if dsn:
        return dsn.replace("postgresql+asyncpg://", "postgresql://")
    user = dot_env.get("POSTGRES_USER", "postgres")
    pwd  = dot_env.get("POSTGRES_PASSWORD", "postgres")
    db   = dot_env.get("POSTGRES_DB", "hypercode")
    return f"postgresql://{user}:{pwd}@postgres:5432/{db}"


DB_DSN  = resolve_db_dsn()
HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

CHECKS = [
    {
        "name": "hypercode-core-health",
        "type": "http",
        "target": "http://hypercode-core:8000/health",
        "environment": "production",
        "interval_seconds": 30,
        "thresholds": {"latency_ms": {"warn": 500, "crit": 2000, "window": 60}},
        "tags": ["core", "api", "critical"],
        "enabled": True,
    },
    {
        "name": "healer-agent-health",
        "type": "http",
        "target": "http://healer-agent:8008/health",
        "environment": "production",
        "interval_seconds": 30,
        "thresholds": {"latency_ms": {"warn": 500, "crit": 2000, "window": 60}},
        "tags": ["healer", "self-heal", "critical"],
        "enabled": True,
    },
    {
        "name": "grafana-health",
        "type": "http",
        "target": "http://grafana:3000/api/health",
        "environment": "production",
        "interval_seconds": 60,
        "thresholds": {"latency_ms": {"warn": 1000, "crit": 5000, "window": 120}},
        "tags": ["observability", "grafana"],
        "enabled": True,
    },
    {
        "name": "redis-cache-health",
        "type": "cache",
        "target": "redis://redis:6379/0",
        "environment": "production",
        "interval_seconds": 20,
        # loosened: 100→200ms warn (Docker network overhead), 500→1000ms crit
        "thresholds": {"latency_ms": {"warn": 200, "crit": 1000, "window": 60}},
        "tags": ["cache", "redis", "critical"],
        "enabled": True,
    },
    {
        "name": "postgres-db-health",
        "type": "db",
        "target": DB_DSN,
        "environment": "production",
        "interval_seconds": 30,
        # loosened: 200→500ms warn (first connection + asyncpg overhead), 1000→2000ms crit
        "thresholds": {"latency_ms": {"warn": 500, "crit": 2000, "window": 60}},
        "tags": ["database", "postgres", "critical"],
        "enabled": True,
    },
]


def seed():
    print(f"\n\U0001f9e0 HyperHealth Seed Script{'  [--force / update mode]' if FORCE else ''}")
    print(f"\U0001f3af API : {API_BASE}")
    print(f"\U0001f511 Key : {API_KEY[:8]}...")
    print(f"\U0001f5c4\ufe0f  DB  : {DB_DSN[:60]}...\n")

    created = skipped = failed = updated = 0

    with httpx.Client(base_url=API_BASE, headers=HEADERS, timeout=15) as client:
        # Fetch ALL checks (including disabled) to map name -> id
        existing_resp = client.get("/checks", params={"enabled_only": False})
        existing: dict[str, str] = {}   # name -> id
        if existing_resp.status_code == 200:
            for c in existing_resp.json():
                existing[c["name"]] = c["id"]

        for check in CHECKS:
            name = check["name"]
            exists = name in existing

            if exists and not FORCE:
                print(f"  \u23ed\ufe0f  SKIP     {name}")
                skipped += 1
                continue

            if exists and FORCE:
                # PATCH existing check in-place (no delete — avoids unique constraint)
                resp = client.patch(f"/checks/{existing[name]}", json={
                    "target":           check["target"],
                    "thresholds":       check["thresholds"],
                    "interval_seconds": check["interval_seconds"],
                    "tags":             check["tags"],
                    "enabled":          True,   # re-enable if it was soft-deleted
                })
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"  \u2705 UPDATED  {data['name']}  [{data['type']}]  target={data['target'][:40]}...")
                    updated += 1
                else:
                    print(f"  \u274c FAILED   {name}  PATCH status={resp.status_code}  {resp.text}")
                    failed += 1
                continue

            # Create new
            resp = client.post("/checks", json=check)
            if resp.status_code == 201:
                data = resp.json()
                print(f"  \u2705 CREATED  {data['name']}  [{data['type']}]  every {data['interval_seconds']}s  id={data['id'][:8]}...")
                created += 1
            else:
                print(f"  \u274c FAILED   {name}  POST status={resp.status_code}  {resp.text}")
                failed += 1

    print(f"\n\U0001f4ca Results: {created} created | {updated} updated | {skipped} skipped | {failed} failed")

    if created + updated > 0:
        print("\n\U0001f525 Workers will execute checks within 30s!")
        print("\U0001f4c8 Grafana  : http://localhost:3001")
        print("\U0001f9ea Report   : curl -H \"X-API-Key: $API_KEY\" \"http://localhost:8095/health/report?env=production\"")
        print("\U0001f4ca Metrics  : curl http://localhost:8095/metrics")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    seed()
