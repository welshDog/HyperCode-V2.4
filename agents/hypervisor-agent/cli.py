#!/usr/bin/env python3
"""
🧬 HyperVisor CLI Dashboard
Real-time monitoring and control for laptop resources.
"""

import requests
import json
import os
import sys
import asyncio
import websockets
from datetime import datetime
from typing import Dict, Any
import click
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import Progress, BarColumn, PercentageColumn
from rich import box

console = Console()

HYPERVISOR_URL = os.getenv("HYPERVISOR_URL", "http://127.0.0.1:8094")
HYPERVISOR_WS = os.getenv("HYPERVISOR_WS", "ws://127.0.0.1:8094")

# ─── CLI Commands ────────────────────────────────────────────────────
@click.group()
def cli():
    """🧬 HyperVisor Agent CLI — Resource Guardian"""
    pass


@cli.command()
def status():
    """Check HyperVisor health."""
    try:
        resp = requests.get(f"{HYPERVISOR_URL}/health", timeout=5)
        data = resp.json()
        console.print(f"✅ {data['agent']} is healthy")
    except Exception as e:
        console.print(f"❌ HyperVisor unavailable: {e}", style="red")
        sys.exit(1)


@cli.command()
def metrics():
    """Show current system and container metrics."""
    try:
        resp = requests.get(f"{HYPERVISOR_URL}/metrics", timeout=5)
        data = resp.json()
        
        sys_m = data["system"]
        
        # System panel
        sys_table = Table(box=box.ROUNDED, title="🖥️ System Metrics")
        sys_table.add_column("Metric", style="cyan")
        sys_table.add_column("Value", style="green")
        
        sys_table.add_row("CPU", f"{sys_m['cpu_percent']:.1f}% ({sys_m['cpu_count']} cores)")
        sys_table.add_row("RAM", f"{sys_m['ram_percent']:.1f}% ({sys_m['ram_available_mb']:.0f}MB free)")
        sys_table.add_row("Disk", f"{sys_m['disk_percent']:.1f}%")
        sys_table.add_row("Containers", f"{data['running_containers']} running / {sys_m['container_count']} total")
        sys_table.add_row("Active Alerts", f"[red]{data['active_alerts']}[/red]" if data['active_alerts'] > 0 else "0")
        
        console.print(sys_table)
        
        # Container table
        if data["containers"]:
            cont_table = Table(box=box.ROUNDED, title="📦 Containers", max_width=120)
            cont_table.add_column("Name", style="cyan")
            cont_table.add_column("State", style="magenta")
            cont_table.add_column("CPU", justify="right")
            cont_table.add_column("Memory", justify="right")
            cont_table.add_column("Restarts", justify="right")
            
            for c in data["containers"]:
                if c["state"] == "running":
                    mem_pct = f"[red]{c['memory_percent']:.0f}%[/red]" if c['memory_percent'] > 90 else f"{c['memory_percent']:.0f}%"
                else:
                    mem_pct = f"[dim]{c['memory_percent']:.0f}%[/dim]"
                
                cont_table.add_row(
                    c["container_name"][:40],
                    c["state"],
                    f"{c['cpu_percent']:.1f}%",
                    f"{c['memory_mb']:.0f}MB {mem_pct}",
                    str(c["restart_count"]),
                )
            
            console.print(cont_table)
    
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        sys.exit(1)


@cli.command()
def alerts():
    """Show recent alerts."""
    try:
        resp = requests.get(f"{HYPERVISOR_URL}/alerts", timeout=5)
        data = resp.json()
        
        if not data["alerts"]:
            console.print("✅ No active alerts", style="green")
            return
        
        alert_table = Table(box=box.ROUNDED, title="🚨 Active Alerts")
        alert_table.add_column("Level", style="magenta")
        alert_table.add_column("Category", style="cyan")
        alert_table.add_column("Message", style="yellow")
        alert_table.add_column("Time", style="dim")
        
        for alert in data["alerts"]:
            color_map = {"crit": "red", "warn": "yellow", "info": "blue"}
            level_style = color_map.get(alert["level"], "white")
            alert_table.add_row(
                f"[{level_style}]{alert['level'].upper()}[/{level_style}]",
                alert["category"],
                alert["message"],
                alert["timestamp"][-8:],
            )
        
        console.print(alert_table)
    
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")


@cli.command()
def scale():
    """Trigger auto-scaling (kill zombies, stop non-critical containers)."""
    try:
        resp = requests.post(f"{HYPERVISOR_URL}/scale", timeout=10)
        data = resp.json()
        console.print(f"✅ Auto-scaling triggered", style="green")
        console.print(f"   RAM: {data['ram_percent']:.1f}%")
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")


@cli.command()
def watch():
    """Watch metrics live (WebSocket stream)."""
    async def stream():
        uri = f"{HYPERVISOR_WS}/ws/metrics"
        
        try:
            async with websockets.connect(uri) as ws:
                console.print("🔴 LIVE — Metrics streaming (Ctrl+C to exit)", style="green")
                
                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    
                    if data["type"] == "metrics":
                        sys_m = data["system"]
                        
                        # Clear and redraw
                        console.clear()
                        
                        # Layout
                        layout = Layout()
                        layout.split_column(
                            Layout(name="system", size=8),
                            Layout(name="alerts", size=10),
                            Layout(name="containers", size=20),
                        )
                        
                        # System
                        sys_panel = f"""
╭─ 🖥️ SYSTEM ─────────────────────────────────────────
│ CPU: {sys_m['cpu_percent']:>6.1f}% | RAM: {sys_m['ram_percent']:>6.1f}% | DISK: {sys_m['disk_percent']:>6.1f}%
│ Free: {sys_m['ram_available_mb']:>8.0f}MB | Containers: {data['running_containers']:>2d} running
╰─────────────────────────────────────────────────────
"""
                        layout["system"].update(Panel(sys_panel, expand=False))
                        
                        # Alerts
                        alerts_list = "\n".join([
                            f"  {a['level'].upper()}: {a['message']}"
                            for a in data["alerts"]
                        ]) if data["alerts"] else "  ✅ No alerts"
                        layout["alerts"].update(Panel(alerts_list, title="🚨 ALERTS", expand=False))
                        
                        # Containers
                        cont_lines = []
                        for c in data["containers"][:5]:
                            cont_lines.append(
                                f"  {c['container_name'][:20]:20s} | CPU: {c['cpu_percent']:>5.1f}% | MEM: {c['memory_mb']:>6.0f}MB"
                            )
                        layout["containers"].update(Panel("\n".join(cont_lines), title="📦 TOP CONTAINERS", expand=False))
                        
                        console.print(layout)
                        await asyncio.sleep(2)
        
        except Exception as e:
            console.print(f"❌ WebSocket error: {e}", style="red")
    
    asyncio.run(stream())


# ─── Main ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    cli()
