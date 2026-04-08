import typer
import requests
import os
from rich.console import Console
from rich.table import Table
from typing import Optional
from jira.models import TicketType, TicketPayload
from jira.templates import TEMPLATES
from jira.generator import generate_json_payload, generate_csv_payload
from jira.validator import validate_ticket

app = typer.Typer()
console = Console()

BASE_URL = os.getenv("HYPERCODE_API_URL", "http://localhost:8000")
API_KEY = os.getenv("HYPERCODE_API_KEY", "dev-key") # Default for dev

@app.command()
def agents():
    """List available agents."""
    try:
        response = requests.get(f"{BASE_URL}/agents/")
        if response.status_code != 200:
             console.print(f"[red]Failed to fetch agents: {response.status_code}[/red]")
             return
             
        agents = response.json()
        
        table = Table(title="HyperCode Agents Swarm")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Capabilities", style="green")
        
        for agent in agents:
            caps = ", ".join([c["name"] for c in agent.get("capabilities", [])])
            table.add_row(agent["id"][:8], agent["name"], caps)
            
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")

@app.command()
def run(task: str):
    """Submit a task to the swarm."""
    console.print(f"[yellow]Submitting task:[/yellow] {task}")
    try:
        # Find Coder
        agents_resp = requests.get(f"{BASE_URL}/agents/")
        agents = agents_resp.json()
        # Simple selection logic
        if not agents:
             console.print("[red]No agents online![/red]")
             return
             
        # Chat
        payload = {
            "messages": [{"role": "user", "content": task}],
            "model": "gpt-4o"
        }
        headers = {"X-API-Key": API_KEY}
        
        resp = requests.post(f"{BASE_URL}/agents/chat", json=payload, headers=headers)
        
        if resp.status_code == 200:
            data = resp.json()
            console.print(f"[green]Response:[/green]\n{data.get('response')}")
        else:
             console.print(f"[red]Error {resp.status_code}:[/red] {resp.text}")
        
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")

@app.command()
def costs():
    """Check project costs."""
    try:
        response = requests.get(f"{BASE_URL}/metrics/costs")
        if response.status_code != 200:
            console.print(f"[red]Failed to fetch costs: {response.status_code}[/red]")
            return

        data = response.json()
        
        console.print(f"[bold]Total Cost:[/bold] ${data['total_cost']}")
        console.print(f"[bold]Total Tokens:[/bold] {data['total_tokens']}")
        
        table = Table(title="Cost by Model")
        table.add_column("Model")
        table.add_column("Cost")
        
        for model, cost in data['by_model'].items():
            table.add_row(model, f"${cost}")
            
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")

if __name__ == "__main__":
    app()

@app.command()
def jira_generate(
    template: str = typer.Option(..., help="Template key"),
    project_key: str = typer.Option(...),
    output: str = typer.Option("json", help="json or csv"),
    assignee: Optional[str] = typer.Option(None),
    priority: str = typer.Option("Medium"),
    epic_link: Optional[str] = typer.Option(None),
    labels: Optional[str] = typer.Option(None, help="comma-separated")
):
    if template not in TEMPLATES:
        console.print(f"[red]Unknown template: {template}[/red]")
        raise typer.Exit(code=1)
    base = TEMPLATES[template](project_key)
    base.priority = priority
    base.assignee = assignee
    base.epic_link = epic_link
    if labels:
        base.labels = [l.strip() for l in labels.split(",") if l.strip()]
    errors = validate_ticket(base)
    if errors:
        console.print("[red]Validation errors:[/red]")
        for e in errors:
            console.print(f"- {e}")
        raise typer.Exit(code=1)
    if output.lower() == "json":
        payload = generate_json_payload(base)
        console.print_json(data=payload)
    elif output.lower() == "csv":
        line = generate_csv_payload(base)
        console.print(line)
    else:
        console.print("[red]Unsupported output format[/red]")
        raise typer.Exit(code=1)

@app.command()
def jira_validate(
    project_key: str,
    summary: str,
    description: str,
    issue_type: TicketType,
    priority: str,
    assignee: Optional[str] = None,
    labels: Optional[str] = None,
    epic_link: Optional[str] = None,
):
    lbls = [l.strip() for l in (labels or "").split(",") if l.strip()]
    ticket = TicketPayload(
        project_key=project_key,
        summary=summary,
        description=description,
        issue_type=issue_type,
        priority=priority,
        assignee=assignee,
        labels=lbls,
        epic_link=epic_link,
    )
    errors = validate_ticket(ticket)
    if errors:
        console.print("[red]Invalid ticket:[/red]")
        for e in errors:
            console.print(f"- {e}")
        raise typer.Exit(code=1)
    console.print("[green]Valid[/green]")
