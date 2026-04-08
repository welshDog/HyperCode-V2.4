#!/usr/bin/env python3
"""
🩺 BROski Health Check — HyperCode V2.0
Runs a full diagnostic on local services + GitHub status
Usage: python scripts/hypercode_health_check.py

Port map verified: 2026-03-26 against HYPERFOCUSzone live docker ps
Redis + Postgres checked via docker exec (internal network by design ✔️)
"""

import socket
import subprocess
import urllib.request
import urllib.error
import json
from datetime import datetime

GITHUB_REPO = "welshDog/HyperCode-V2.4"

# ── HTTP SERVICES (port-mapped to Windows localhost) ──
SERVICES = [
    # CORE
    {"name": "🧠 HyperCode Backend",    "port": 8000, "path": "/health"},
    # AGENTS
    {"name": "🩺 Healer Agent",          "port": 8010, "path": "/health"},
    {"name": "🎛️  Crew Orchestrator",    "port": 8081, "path": "/health"},
    {"name": "🦅 Super BROski Agent",    "port": 8015, "path": "/health"},
    {"name": "⚡ Throttle Agent",          "port": 8014, "path": "/health"},
    {"name": "🧪 Test Agent",             "port": 8013, "path": "/health"},
    {"name": "📝 Tips & Tricks Writer",   "port": 8011, "path": "/health"},
    # DASHBOARDS
    {"name": "📊 Mission Control",        "port": 8088, "path": "/"},
    {"name": "🌍 Hyper Mission UI",       "port": 8099, "path": "/"},
    {"name": "📈 Grafana",                "port": 3001, "path": "/"},
    {"name": "🔍 cAdvisor",               "port": 8090, "path": "/"},
    {"name": "📁 Prometheus",             "port": 9090, "path": "/-/healthy"},
    # MCP
    {"name": "🔗 MCP Gateway",            "port": 8820, "path": "/health"},
    {"name": "🔗 MCP REST Adapter",       "port": 8821, "path": "/health"},
    # AI
    {"name": "🤖 Ollama LLM",             "port": 11434, "path": "/api/tags"},
    {"name": "🧠 Chroma Vector DB",       "port": 8009,  "path": "/api/v1/heartbeat"},
    # STORAGE (TCP only)
    {"name": "🪣 MinIO Storage",          "port": 9000,  "path": None},
]

# ── INTERNAL DOCKER SERVICES (no Windows port — check via docker exec) ──
DOCKER_EXEC_CHECKS = [
    {
        "name": "🗄️  Redis",
        "container": "redis",
        "cmd": ["docker", "exec", "redis", "redis-cli", "ping"],
        "expect": "PONG",
    },
    {
        "name": "🐘 PostgreSQL",
        "container": "postgres",
        "cmd": ["docker", "exec", "postgres", "pg_isready", "-U", "postgres"],
        "expect": "accepting connections",
    },
]

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):     print(f"  {GREEN}✅ {msg}{RESET}")
def fail(msg):   print(f"  {RED}❌ {msg}{RESET}")
def warn(msg):   print(f"  {YELLOW}⚠️  {msg}{RESET}")
def info(msg):   print(f"  {CYAN}ℹ️  {msg}{RESET}")
def header(msg): print(f"\n{BOLD}{CYAN}{msg}{RESET}")

def check_port(port, timeout=2):
    try:
        with socket.create_connection(("localhost", port), timeout=timeout):
            return True
    except Exception:
        return False

def check_http(port, path, timeout=3):
    try:
        req = urllib.request.urlopen(f"http://localhost:{port}{path}", timeout=timeout)
        return req.status, True
    except urllib.error.HTTPError as e:
        return e.code, True
    except Exception:
        return None, False

def check_docker_exec(cmd, expect):
    """Run a command inside a container and check output."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        output = result.stdout + result.stderr
        return expect.lower() in output.lower()
    except Exception:
        return False

def check_docker_engine():
    """Check Docker engine via 'docker info' — more reliable than 'docker ps' on Windows."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=8
        )
        if result.returncode == 0:
            containers = [c for c in result.stdout.strip().split("\n") if c]
            return True, containers
        # Fallback: docker info
        info_result = subprocess.run(
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            capture_output=True, text=True, timeout=8
        )
        if info_result.returncode == 0:
            return True, []
        return False, []
    except Exception:
        return False, []

def check_github():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/commits/main"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BROski-HealthCheck/1.0"})
        response = urllib.request.urlopen(req, timeout=5)
        data = json.loads(response.read())
        msg  = data["commit"]["message"].split("\n")[0][:60]
        date = data["commit"]["author"]["date"]
        sha  = data["sha"][:7]
        return True, sha, msg, date
    except Exception as e:
        return False, None, str(e), None

def check_github_ci():
    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/runs?per_page=3"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BROski-HealthCheck/1.0"})
        response = urllib.request.urlopen(req, timeout=5)
        data = json.loads(response.read())
        runs = data.get("workflow_runs", [])
        if not runs:
            return True, "none", "none", "No runs found"
        # Find most recent non-skipped run
        for run in runs:
            if run["conclusion"] not in ("skipped", None) or run["status"] == "in_progress":
                return True, run["status"], run["conclusion"] or "pending", run["name"]
        return True, "disabled", "paused", "All workflows paused"
    except Exception as e:
        return False, None, None, str(e)

def main():
    print(f"\n{BOLD}{'='*58}")
    print(f"  🩺 BROski♾ HYPERCODE HEALTH CHECK — HYPERFOCUSzone")
    print(f"  🏴󠁧󠁢󠁷󠁬󠁳󠁿  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*58}{RESET}")

    score = 0
    total = 0
    offline = []

    # ── HTTP SERVICES ──
    header("🖥️  LOCAL SERVICES")
    for svc in SERVICES:
        total += 1
        port_alive = check_port(svc["port"])
        if not port_alive:
            fail(f"{svc['name']} — :{svc['port']} OFFLINE")
            offline.append(svc["name"])
            continue
        if svc["path"]:
            status_code, http_ok = check_http(svc["port"], svc["path"])
            if http_ok:
                ok(f"{svc['name']} — :{svc['port']} ONLINE (HTTP {status_code})")
                score += 1
            else:
                warn(f"{svc['name']} — :{svc['port']} port open, HTTP silent")
                score += 0.5
        else:
            ok(f"{svc['name']} — :{svc['port']} ONLINE (TCP)")
            score += 1

    # ── INTERNAL DOCKER SERVICES ──
    header("🔒 INTERNAL SERVICES (Docker network)")
    for svc in DOCKER_EXEC_CHECKS:
        total += 1
        alive = check_docker_exec(svc["cmd"], svc["expect"])
        if alive:
            ok(f"{svc['name']} — healthy inside Docker 🐳")
            score += 1
        else:
            fail(f"{svc['name']} — container not responding")
            offline.append(svc["name"])

    # ── DOCKER ENGINE ──
    header("🐋 DOCKER ENGINE")
    total += 1
    docker_alive, containers = check_docker_engine()
    if docker_alive:
        ok(f"Docker engine ONLINE — {len(containers)} container(s) running")
        score += 1
        for c in containers[:10]:
            info(f"  └─ {c}")
        if len(containers) > 10:
            info(f"  └─ ... and {len(containers)-10} more")
    else:
        fail("Docker engine OFFLINE")
        warn("Fix: restart Docker Desktop from system tray")

    # ── GITHUB ──
    header("🐙 GITHUB STATUS")
    total += 1
    gh_ok, sha, msg, date = check_github()
    if gh_ok:
        ok(f"Latest commit: [{sha}] {msg}")
        info(f"Pushed: {date}")
        score += 1
    else:
        fail(f"GitHub API unreachable: {msg}")

    # ── CI/CD ──
    total += 1
    ci_ok, status, conclusion, name = check_github_ci()
    if ci_ok:
        if conclusion == "success":
            ok(f"CI: {name} — PASSED ✅")
            score += 1
        elif conclusion == "paused" or status == "disabled":
            ok(f"CI: Workflows paused 💤 — saving BROski$ 💰")
            score += 1
        elif status == "in_progress":
            warn(f"CI: {name} — RUNNING ⏳")
            score += 0.5
        elif conclusion in ("failure", "cancelled"):
            fail(f"CI: {name} — {conclusion.upper()}")
        else:
            warn(f"CI: {name} — {status}/{conclusion}")
            score += 0.5
    else:
        warn(f"CI check failed: {name}")

    # ── OFFLINE SUMMARY ──
    if offline:
        header("🚨 NEEDS ATTENTION")
        for o in offline:
            warn(f"{o}")

    # ── FINAL SCORE ──
    pct = int((score / total) * 100)
    print(f"\n{BOLD}{'='*58}")
    if pct >= 80:
        print(f"  🔥 HYPERSTATUS: {GREEN}FULLY OPERATIONAL — {pct}%{RESET}{BOLD}")
        print(f"  🦅 BROski Power Level: LEGENDARY ♾")
    elif pct >= 60:
        print(f"  ⚡ HYPERSTATUS: {YELLOW}GOOD — {pct}%{RESET}{BOLD}")
        print(f"  🛠️  BROski Power Level: SOLID FOUNDATION")
    elif pct >= 40:
        print(f"  ⚡ HYPERSTATUS: {YELLOW}PARTIAL — {pct}%{RESET}{BOLD}")
        print(f"  🛠️  BROski Power Level: NEEDS SOME LOVE")
    else:
        print(f"  🚨 HYPERSTATUS: {RED}CRITICAL — {pct}%{RESET}{BOLD}")
        print(f"  🩺 BROski Power Level: HEALER NEEDED")
    print(f"  Score: {score:.1f}/{total} services healthy")
    print(f"{'='*58}{RESET}\n")

if __name__ == "__main__":
    main()
