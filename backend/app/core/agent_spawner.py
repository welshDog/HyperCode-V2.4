from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol

from ruamel.yaml import YAML


class AgentSpawnerError(RuntimeError):
    pass


yaml = YAML(typ="safe")


def find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for candidate in [cur, *cur.parents]:
        if (candidate / "docker-compose.yml").exists():
            return candidate
    raise AgentSpawnerError("Unable to locate repo root containing docker-compose.yml")


def list_profile_services(*, compose_path: Path, profile: str) -> list[str]:
    raw = compose_path.read_text(encoding="utf-8", errors="ignore")
    doc = yaml.load(raw) or {}
    services = doc.get("services") or {}
    if not isinstance(services, dict):
        return []

    found: list[str] = []
    for name, spec in services.items():
        if not isinstance(spec, dict):
            continue
        profiles = spec.get("profiles") or []
        if isinstance(profiles, str):
            profiles = [profiles]
        if not isinstance(profiles, list):
            continue
        if profile in profiles:
            found.append(str(name))
    return sorted(set(found))


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


class CommandRunner(Protocol):
    def run(self, args: list[str], *, cwd: Path) -> CommandResult: ...


class SubprocessRunner:
    def run(self, args: list[str], *, cwd: Path) -> CommandResult:
        completed = subprocess.run(
            args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        return CommandResult(
            returncode=int(completed.returncode),
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
        )


def _split_lines(text: str) -> set[str]:
    return {line.strip() for line in (text or "").splitlines() if line.strip()}


@dataclass
class AgentSpawner:
    repo_root: Path
    compose_file: Path
    profile: str = "agents"
    runner: CommandRunner = SubprocessRunner()

    def available_agents(self) -> list[str]:
        return list_profile_services(compose_path=self.compose_file, profile=self.profile)

    def ensure_available(self, agent: str) -> None:
        if agent not in self.available_agents():
            available = ", ".join(self.available_agents())
            raise AgentSpawnerError(f"Unknown agent '{agent}'. Available: {available}")

    def _docker_names(self, *, all_containers: bool) -> set[str]:
        args = ["docker", "ps", "--format", "{{.Names}}"]
        if all_containers:
            args.insert(2, "-a")
        res = self.runner.run(args, cwd=self.repo_root)
        if res.returncode != 0:
            raise AgentSpawnerError((res.stderr or res.stdout or "docker ps failed").strip())
        return _split_lines(res.stdout)

    def is_running(self, name: str) -> bool:
        return name in self._docker_names(all_containers=False)

    def exists(self, name: str) -> bool:
        return name in self._docker_names(all_containers=True)

    def restart(self, name: str) -> None:
        res = self.runner.run(["docker", "restart", name], cwd=self.repo_root)
        if res.returncode != 0:
            raise AgentSpawnerError((res.stderr or res.stdout or f"Failed to restart {name}").strip())

    def spawn(self, service: str, *, dry_run: bool = False) -> list[str]:
        self.ensure_available(service)
        args = ["docker", "compose", "--profile", self.profile, "up", "-d", service]
        if dry_run:
            return args
        res = self.runner.run(args, cwd=self.repo_root)
        if res.returncode != 0:
            raise AgentSpawnerError((res.stderr or res.stdout or "docker compose up failed").strip())
        return args

    def ensure_running(self, service: str, *, dry_run: bool = False) -> str:
        self.ensure_available(service)
        if self.is_running(service):
            return "already_running"
        if self.exists(service):
            if dry_run:
                return "would_restart"
            self.restart(service)
            return "restarted"
        self.spawn(service, dry_run=dry_run)
        return "spawned" if not dry_run else "would_spawn"


def make_spawner(
    *,
    start: Path | None = None,
    compose_filename: str = "docker-compose.yml",
    profile: str = "agents",
    runner: CommandRunner | None = None,
) -> AgentSpawner:
    repo_root = find_repo_root(start or Path.cwd())
    compose_file = repo_root / compose_filename
    if not compose_file.exists():
        raise AgentSpawnerError(f"Compose file not found: {compose_file}")
    return AgentSpawner(
        repo_root=repo_root,
        compose_file=compose_file,
        profile=profile,
        runner=runner or SubprocessRunner(),
    )


def python_bin() -> str:
    return sys.executable or "python"

