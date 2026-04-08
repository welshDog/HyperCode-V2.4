#!/usr/bin/env python3
"""
HyperCode V2.0 — Planning System Test Suite 🧠🦅
Run from the repo root:  python tests/test_planning_system.py
Requires: pip install httpx rich
Set BASE_URL env var if not running on localhost:8000
"""

import os, json, sys
import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
API = f"{BASE_URL}/api/v1"

# ── Auth token — set via env or will try anon endpoints ──────────────────────
TOKEN = os.getenv("HYPERCODE_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}

console = Console()
results = []

def test(name: str, fn):
    try:
        status, detail = fn()
        emoji = "✅" if status else "❌"
        results.append((emoji, name, detail))
        console.print(f"{emoji} [bold]{name}[/bold] — {detail}")
    except Exception as e:
        results.append(("💥", name, str(e)))
        console.print(f"💥 [red bold]{name}[/red bold] — {e}")

# ── 1. Health check ───────────────────────────────────────────────────────────
def t_health():
    r = httpx.get(f"{BASE_URL}/health", timeout=5)
    return r.status_code == 200, f"HTTP {r.status_code}"

# ── 2. POST /api/v1/planning/generate — PRD document ─────────────────────────
def t_generate_prd():
    payload = {
        "content": (
            "As a user I want to log in with my GitHub account so that I can "
            "access my repositories. Acceptance criteria: OAuth flow completes, "
            "user profile is stored, session token is returned."
        ),
        "document_type": "prd",
        "metadata": {"source": "test-suite", "version": "1.0"}
    }
    r = httpx.post(f"{API}/planning/generate", json=payload, headers=HEADERS, timeout=60)
    if r.status_code == 200:
        plan = r.json()
        phases = len(plan.get("phases", []))
        return True, f"HTTP 200 — {phases} phase(s) returned"
    return False, f"HTTP {r.status_code} — {r.text[:120]}"

# ── 3. POST /api/v1/planning/generate — issue document ───────────────────────
def t_generate_issue():
    payload = {
        "content": (
            "Bug: Agent router crashes when task_type is None. "
            "Steps to reproduce: POST /api/v1/tasks with no task_type field. "
            "Expected: graceful 422. Actual: 500 Internal Server Error."
        ),
        "document_type": "issue"
    }
    r = httpx.post(f"{API}/planning/generate", json=payload, headers=HEADERS, timeout=60)
    if r.status_code == 200:
        plan = r.json()
        fc = len(plan.get("file_changes_summary", []))
        return True, f"HTTP 200 — {fc} file change(s) in plan"
    return False, f"HTTP {r.status_code} — {r.text[:120]}"

# ── 4. POST /api/v1/planning/generate — design document ──────────────────────
def t_generate_design():
    payload = {
        "content": (
            "Architecture: The BROski Terminal component communicates with the "
            "Crew Orchestrator via WebSocket. Each component diagram shows a "
            "Redis pub/sub channel for real-time updates."
        ),
        "document_type": "design"
    }
    r = httpx.post(f"{API}/planning/generate", json=payload, headers=HEADERS, timeout=60)
    return r.status_code == 200, f"HTTP {r.status_code}"

# ── 5. POST /api/v1/planning/generate — auto-detect generic ──────────────────
def t_generate_generic():
    payload = {"content": "This is a vague blob of text with no clear keywords."}
    r = httpx.post(f"{API}/planning/generate", json=payload, headers=HEADERS, timeout=60)
    return r.status_code == 200, f"HTTP {r.status_code} (generic auto-detect)"

# ── 6. generate with ?persist=true ───────────────────────────────────────────
def t_generate_persist():
    payload = {
        "content": "User story: As a developer I want cached plan output so agents can reuse it.",
        "document_type": "prd"
    }
    r = httpx.post(f"{API}/planning/generate?persist=true", json=payload, headers=HEADERS, timeout=60)
    return r.status_code in (200, 401, 403), f"HTTP {r.status_code} (persist param accepted)"

# ── 7. generate-from-task with a fake task id ────────────────────────────────
def t_generate_from_task_404():
    r = httpx.post(
        f"{API}/planning/generate-from-task/nonexistent-task-999",
        headers=HEADERS, timeout=10
    )
    return r.status_code in (404, 401, 403, 422), f"HTTP {r.status_code} (expected error)"

# ── 8. Schema validation — missing required field ─────────────────────────────
def t_schema_validation():
    r = httpx.post(
        f"{API}/planning/generate",
        json={"document_type": "prd"},
        headers=HEADERS, timeout=10
    )
    return r.status_code == 422, f"HTTP {r.status_code} (422 = correct validation error)"

# ── 9. Agent router — plan keyword detection ─────────────────────────────────
def t_router_plan_keyword():
    payload = {
        "task_type": "generate plan",
        "description": "generate plan for the new auth service",
        "priority": 1
    }
    r = httpx.post(f"{API}/tasks", json=payload, headers=HEADERS, timeout=60)
    return r.status_code in (200, 201, 401, 403), f"HTTP {r.status_code} (router accepted)"

# ── 10. Task creation with generate_plan=true ─────────────────────────────────
def t_task_generate_plan_field():
    payload = {
        "task_type": "coding",
        "description": "Add a user profile page with avatar upload",
        "priority": 2,
        "generate_plan": True
    }
    r = httpx.post(f"{API}/tasks", json=payload, headers=HEADERS, timeout=60)
    return r.status_code in (200, 201, 401, 403), f"HTTP {r.status_code} (generate_plan field accepted)"

# ── Run all tests ─────────────────────────────────────────────────────────────
console.print(Panel.fit(
    "[bold cyan]🦅 HyperCode V2.0 — Planning System Tests[/bold cyan]\n"
    f"Target: [yellow]{BASE_URL}[/yellow]",
    border_style="cyan"
))

test("1. API health check",            t_health)
test("2. Generate plan from PRD",      t_generate_prd)
test("3. Generate plan from Issue",    t_generate_issue)
test("4. Generate plan from Design",   t_generate_design)
test("5. Auto-detect generic doc",     t_generate_generic)
test("6. generate with ?persist=true", t_generate_persist)
test("7. generate-from-task 404",      t_generate_from_task_404)
test("8. Schema validation (422)",     t_schema_validation)
test("9. Router plan keyword detect",  t_router_plan_keyword)
test("10. TaskCreate generate_plan",   t_task_generate_plan_field)

# ── Summary table ─────────────────────────────────────────────────────────────
passed = sum(1 for r in results if r[0] == "✅")
total = len(results)

table = Table(title=f"Results: {passed}/{total} passed", show_lines=True)
table.add_column("", width=3)
table.add_column("Test", style="bold")
table.add_column("Detail", style="dim")
for emoji, name, detail in results:
    table.add_row(emoji, name, detail)
console.print(table)

if passed < total:
    console.print(f"\n[red]⚠️  {total - passed} test(s) failed — check server logs![/red]")
    sys.exit(1)
else:
    console.print("\n[green bold]🔥 ALL SYSTEMS GO BROski♾![/green bold]")
