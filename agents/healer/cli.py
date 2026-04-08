import typer
import asyncio
import os
import sys

# Ensure we can import healer package
try:
    from agents.healer.adapters.docker_adapter import DockerAdapter
except ImportError:
    # Attempt to patch sys.path to find 'healer'
    # Assume we are in .../agents/healer/cli.py
    # We want to add .../agents to sys.path so 'import healer' works.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir) # agents
    if parent_dir not in sys.path:
        sys.path.append(parent_dir)
    
    try:
        from agents.healer.adapters.docker_adapter import DockerAdapter
    except ImportError:
        # Fallback: try adding project root if agents is not package root
        # .../HyperCode-V2.0/agents/healer -> .../HyperCode-V2.0
        project_root = os.path.dirname(parent_dir)
        if project_root not in sys.path:
            sys.path.append(project_root)
        
        # Try importing via full path if needed, or rely on previous successful import
        try:
            from agents.healer.adapters.docker_adapter import DockerAdapter
        except ImportError:
            raise ImportError("Failed to import Healer Agent components. Check sys.path.")

app = typer.Typer(help="Healer Agent CLI - Manual Intervention Tools")
adapter = DockerAdapter()

@app.command()
def status(name: str):
    """
    Check the health status of a specific container.
    """
    container = adapter.get_container(name)
    if container:
        typer.echo(f"📦 Container: {container.name}")
        typer.echo(f"   Status: {container.status}")
        typer.echo(f"   Health: {container.health}")
        typer.echo(f"   Started: {container.started_at}")
        typer.echo(f"   Restarts: {container.restart_count}")
    else:
        typer.secho(f"❌ Container '{name}' not found or error occurred.", fg=typer.colors.RED)

@app.command()
def restart(name: str, force: bool = False):
    """
    Trigger a container restart.
    Respects the 3-restarts-per-5-min threshold unless --force is used.
    """
    async def _restart():
        typer.echo(f"Attempting to restart {name}...")
        success = await adapter.restart_container(name, force=force)
        if success:
            typer.secho(f"✅ Successfully restarted {name}", fg=typer.colors.GREEN)
        else:
            typer.secho(f"❌ Failed to restart {name}. Check logs or thresholds.", fg=typer.colors.RED)
    
    asyncio.run(_restart())

@app.command()
def logs(name: str, lines: int = 50):
    """
    Fetch the last N lines of logs from a container.
    """
    typer.echo(f"--- Logs for {name} (last {lines} lines) ---")
    logs_content = adapter.get_logs(name, lines)
    typer.echo(logs_content)
    typer.echo("-------------------------------------------")

if __name__ == "__main__":
    app()
