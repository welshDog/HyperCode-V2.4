import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from app.core.agent_spawner import AgentSpawner, AgentSpawnerError, CommandResult, list_profile_services


@dataclass
class FakeRunner:
    responses: dict[tuple[str, ...], CommandResult]
    calls: list[tuple[str, ...]]

    def run(self, args: list[str], *, cwd: Path) -> CommandResult:
        self.calls.append(tuple(args))
        key = tuple(args)
        if key not in self.responses:
            return CommandResult(returncode=1, stdout="", stderr=f"no fake response for: {args}")
        return self.responses[key]


def test_list_profile_services_extracts_agents(tmp_path: Path) -> None:
    compose = tmp_path / "docker-compose.yml"
    compose.write_text(
        """
services:
  web:
    image: nginx
  coder-agent:
    profiles: ["agents"]
  healer:
    profiles: ["ops", "health"]
  mcp-gateway:
    profiles: ["agents"]
""".strip(),
        encoding="utf-8",
    )
    assert list_profile_services(compose_path=compose, profile="agents") == ["coder-agent", "mcp-gateway"]


def test_ensure_available_rejects_unknown_agent(tmp_path: Path) -> None:
    compose = tmp_path / "docker-compose.yml"
    compose.write_text(
        """
services:
  coder-agent:
    profiles: ["agents"]
""".strip(),
        encoding="utf-8",
    )
    runner = FakeRunner(responses={}, calls=[])
    spawner = AgentSpawner(repo_root=tmp_path, compose_file=compose, runner=runner)
    with pytest.raises(AgentSpawnerError) as exc:
        spawner.ensure_available("nope-agent")
    assert "Unknown agent" in str(exc.value)


def test_ensure_running_already_running(tmp_path: Path) -> None:
    compose = tmp_path / "docker-compose.yml"
    compose.write_text(
        """
services:
  coder-agent:
    profiles: ["agents"]
""".strip(),
        encoding="utf-8",
    )
    runner = FakeRunner(
        responses={
            ("docker", "ps", "--format", "{{.Names}}"): CommandResult(returncode=0, stdout="coder-agent\n", stderr=""),
        },
        calls=[],
    )
    spawner = AgentSpawner(repo_root=tmp_path, compose_file=compose, runner=runner)
    assert spawner.ensure_running("coder-agent") == "already_running"


def test_ensure_running_restarts_when_exists_but_stopped(tmp_path: Path) -> None:
    compose = tmp_path / "docker-compose.yml"
    compose.write_text(
        """
services:
  coder-agent:
    profiles: ["agents"]
""".strip(),
        encoding="utf-8",
    )
    runner = FakeRunner(
        responses={
            ("docker", "ps", "--format", "{{.Names}}"): CommandResult(returncode=0, stdout="", stderr=""),
            ("docker", "ps", "-a", "--format", "{{.Names}}"): CommandResult(returncode=0, stdout="coder-agent\n", stderr=""),
            ("docker", "restart", "coder-agent"): CommandResult(returncode=0, stdout="coder-agent\n", stderr=""),
        },
        calls=[],
    )
    spawner = AgentSpawner(repo_root=tmp_path, compose_file=compose, runner=runner)
    assert spawner.ensure_running("coder-agent") == "restarted"
    assert ("docker", "restart", "coder-agent") in runner.calls


def test_ensure_running_spawns_when_missing(tmp_path: Path) -> None:
    compose = tmp_path / "docker-compose.yml"
    compose.write_text(
        """
services:
  coder-agent:
    profiles: ["agents"]
""".strip(),
        encoding="utf-8",
    )
    runner = FakeRunner(
        responses={
            ("docker", "ps", "--format", "{{.Names}}"): CommandResult(returncode=0, stdout="", stderr=""),
            ("docker", "ps", "-a", "--format", "{{.Names}}"): CommandResult(returncode=0, stdout="", stderr=""),
            ("docker", "compose", "--profile", "agents", "up", "-d", "coder-agent"): CommandResult(returncode=0, stdout="", stderr=""),
        },
        calls=[],
    )
    spawner = AgentSpawner(repo_root=tmp_path, compose_file=compose, runner=runner)
    assert spawner.ensure_running("coder-agent") == "spawned"
    assert ("docker", "compose", "--profile", "agents", "up", "-d", "coder-agent") in runner.calls


@pytest.mark.e2e
def test_spawn_agent_script_lists_agents() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "scripts" / "spawn_agent.py"
    completed = subprocess.run(
        [sys.executable, str(script), "--list"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )
    assert completed.returncode == 0, completed.stderr
    assert "coder-agent" in completed.stdout.splitlines()

