from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.agent_spawner import AgentSpawnerError, make_spawner


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="spawn_agent.py")
    p.add_argument("agent", nargs="?", help="Agent service name (docker-compose profile service)")
    p.add_argument("--list", action="store_true", help="List available agents in the compose profile")
    p.add_argument("--profile", default="agents", help="Compose profile to target (default: agents)")
    p.add_argument("--compose", default="docker-compose.yml", help="Compose filename (default: docker-compose.yml)")
    p.add_argument("--dry-run", action="store_true", help="Print the docker command without executing it")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        spawner = make_spawner(start=Path.cwd(), compose_filename=args.compose, profile=args.profile)
    except AgentSpawnerError as e:
        print(str(e), file=sys.stderr)
        return 2

    if args.list or not args.agent:
        agents = spawner.available_agents()
        if not agents:
            print(f"No services found for profile '{args.profile}' in {spawner.compose_file}")
            return 1
        for name in agents:
            print(name)
        return 0 if (args.list or not args.agent) else 2

    agent = str(args.agent).strip()
    if not agent:
        print("Agent name is required.", file=sys.stderr)
        return 2

    try:
        state = spawner.ensure_running(agent, dry_run=bool(args.dry_run))
    except AgentSpawnerError as e:
        print(str(e), file=sys.stderr)
        return 2

    if args.dry_run:
        cmd = ["docker", "compose", "--profile", spawner.profile, "up", "-d", agent]
        print(" ".join(cmd))
    else:
        print(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

