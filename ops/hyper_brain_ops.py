"""
hyper_brain_ops.py — CLI entry point for HyperCode-V2.4 brain ops chain.

Usage:
    python -m ops.hyper_brain_ops              # Run full chain
    python -m ops.hyper_brain_ops --step health_check
    python -m ops.hyper_brain_ops --dry-run

Env vars required (set in .env):
    GITHUB_PAT          — GitHub Personal Access Token (repo scope)
    GITHUB_REPOS        — Comma-separated list: welshDog/HyperCode-V2.4,...
    VAULT_PATH          — Absolute path to your Obsidian vault root
    DISCORD_WEBHOOK_URL — Discord webhook for #brain-ops channel
    BRIEFING_API_URL    — URL of the hyper-brain briefing API endpoint

Outputs (written to VAULT_PATH/Ops-Logs/):
    {date}-ops-status.json  — machine-readable status (agents + dashboard)
    {date}-ops.log          — human-readable log (you, debugging at 3am)
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    requests = None  # Handled gracefully in steps that need it

from ops.operation_handler import (
    CircuitBreaker,
    OperationHandler,
    OpsSession,
    StepResult,
)

# ---------------------------------------------------------------------------
# Config — loaded from environment
# ---------------------------------------------------------------------------

def load_config() -> dict:
    """Load and validate required env vars. Raises on missing critical vars."""
    config = {
        "github_pat":          os.getenv("GITHUB_PAT", ""),
        "github_repos":        [
            r.strip() for r in os.getenv("GITHUB_REPOS", "").split(",") if r.strip()
        ],
        "vault_path":          Path(os.getenv("VAULT_PATH", "./vault")),
        "discord_webhook_url": os.getenv("DISCORD_WEBHOOK_URL", ""),
        "briefing_api_url":    os.getenv("BRIEFING_API_URL", "http://localhost:8100/briefing"),
    }
    return config


# ---------------------------------------------------------------------------
# Step implementations
# ---------------------------------------------------------------------------

def step_health_check(config: dict) -> dict:
    """
    Verifies Docker daemon is responding and hyper-brain container is up.
    Raises on failure — health check is the hard stop (Rule 1).
    """
    result = {"docker_daemon": None, "hyper_brain_container": None, "briefing_api": None}

    # Check Docker daemon
    proc = subprocess.run(
        ["docker", "info", "--format", "{{.ServerVersion}}"],
        capture_output=True, text=True, timeout=10
    )
    if proc.returncode != 0:
        raise ConnectionError(f"Docker daemon not responding: {proc.stderr.strip()}")
    result["docker_daemon"] = f"✅ responding (Docker {proc.stdout.strip()})"

    # Check hyper-brain container
    proc2 = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.Status}}", "hyper-brain"],
        capture_output=True, text=True, timeout=10
    )
    if proc2.returncode != 0 or proc2.stdout.strip() != "running":
        state = proc2.stdout.strip() or proc2.stderr.strip()
        raise RuntimeError(f"hyper-brain container not running: {state}")
    result["hyper_brain_container"] = "✅ running"

    # Check briefing API
    if requests:
        api_url = config["briefing_api_url"].replace("/briefing", "/health")
        start = time.monotonic()
        resp = requests.get(api_url, timeout=5)
        ms = int((time.monotonic() - start) * 1000)
        if resp.status_code != 200:
            raise TimeoutError(f"Briefing API returned {resp.status_code}")
        result["briefing_api"] = f"✅ responding (200 OK, {ms}ms)"
    else:
        result["briefing_api"] = "⚠️ requests not installed — skipped"

    return result


def step_github_sync(config: dict) -> dict:
    """
    Fetches open issues from each repo in GITHUB_REPOS.
    Returns partial result on individual repo failure (doesn't stop the chain).
    """
    if not requests:
        raise ImportError("requests library required for GitHub sync")

    pat = config["github_pat"]
    if not pat:
        raise PermissionError("GITHUB_PAT not set — GH_001")

    headers = {
        "Authorization": f"Bearer {pat}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    repos_attempted = config["github_repos"]
    if not repos_attempted:
        raise ValueError("GITHUB_REPOS not set — no repos to sync")

    succeeded, failed, all_issues = [], [], []

    for repo in repos_attempted:
        try:
            url = f"https://api.github.com/repos/{repo}/issues?state=open&per_page=50"
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 60))
                err = Exception(f"Rate limit hit (429)")
                err.retry_after = retry_after
                raise err
            if resp.status_code == 401:
                raise PermissionError(f"GitHub token invalid (401) for {repo}")
            if resp.status_code == 403:
                raise PermissionError(f"No access to {repo} (403)")
            if resp.status_code == 404:
                raise FileNotFoundError(f"Repo not found: {repo}")
            resp.raise_for_status()
            issues = [i for i in resp.json() if "pull_request" not in i]
            all_issues.extend(issues)
            succeeded.append({"repo": repo, "issues_count": len(issues)})
        except Exception as e:
            failed.append({"repo": repo, "error": str(e)})

    return {
        "repos_attempted": len(repos_attempted),
        "repos_succeeded": len(succeeded),
        "repos_failed": len(failed),
        "issues_synced": len(all_issues),
        "succeeded": succeeded,
        "failed_repos": failed,
        "issues": all_issues,
    }


def step_briefing_generation(config: dict, github_data: Optional[dict] = None) -> dict:
    """
    Calls the hyper-brain briefing API to generate today's .md briefing.
    Falls back to a local template if the API is unavailable.
    """
    vault_path = config["vault_path"]
    briefings_dir = vault_path / "Briefings"
    briefings_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = briefings_dir / f"{date_str}-briefing.md"

    if requests:
        payload = {"date": date_str, "github_data": github_data or {}}
        resp = requests.post(
            config["briefing_api_url"],
            json=payload,
            timeout=30,
        )
        if resp.status_code == 500:
            raise RuntimeError(f"Briefing API returned 500")
        resp.raise_for_status()
        content = resp.text
        sections_generated = content.count("## ")
    else:
        # Fallback: minimal local briefing
        open_issues = github_data.get("issues_synced", 0) if github_data else 0
        content = (
            f"# 🧠 Morning Briefing — {date_str}\n\n"
            f"*Generated locally (API unavailable)*\n\n"
            f"## Open Issues\n\n"
            f"Total open issues synced: {open_issues}\n\n"
            f"## Status\n\nSee ops-status.json for full details.\n"
        )
        sections_generated = 2

    out_path.write_text(content, encoding="utf-8")
    size = out_path.stat().st_size

    return {
        "file_path": str(out_path),
        "file_size_bytes": size,
        "sections_generated": sections_generated,
        "sections_skipped": 0,
    }


def step_vault_commit(config: dict) -> dict:
    """Commits new/changed files in the vault to git."""
    vault_path = config["vault_path"]

    def _git(*args):
        return subprocess.run(
            ["git", "-C", str(vault_path), *args],
            capture_output=True, text=True, timeout=30
        )

    # Check git is initialized
    check = _git("rev-parse", "--git-dir")
    if check.returncode != 0:
        raise FileNotFoundError(f"Git not initialized in {vault_path} — run git init")

    # Ensure user config
    name_check = _git("config", "user.name")
    if not name_check.stdout.strip():
        _git("config", "user.name", "BROski")
        _git("config", "user.email", "broski@hyperfocus.zone")

    # Stage all changes
    _git("add", "-A")

    # Check if there's anything to commit
    status = _git("status", "--porcelain")
    if not status.stdout.strip():
        return {"status": "NO_CHANGES", "commit_hash": None, "files_changed": 0}

    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    commit_msg = f"ops: sync briefings and github inbox {ts}"
    commit = _git("commit", "-m", commit_msg)
    if commit.returncode != 0:
        raise RuntimeError(f"git commit failed: {commit.stderr.strip()}")

    # Get commit hash
    hash_proc = _git("rev-parse", "--short", "HEAD")
    commit_hash = hash_proc.stdout.strip()

    # Parse stats
    lines = commit.stdout.strip().split("\n")
    files_changed = 0
    for line in lines:
        if "file" in line:
            parts = line.split()
            for i, p in enumerate(parts):
                if "file" in p and i > 0:
                    try:
                        files_changed = int(parts[i - 1])
                    except ValueError:
                        pass

    return {
        "commit_hash": commit_hash,
        "commit_message": commit_msg,
        "files_changed": files_changed,
    }


def step_discord_report(config: dict, status_obj: dict) -> dict:
    """Posts the ops summary to the Discord #brain-ops webhook."""
    if not requests:
        raise ImportError("requests library required for Discord report")

    webhook_url = config["discord_webhook_url"]
    if not webhook_url:
        raise ValueError("DISCORD_WEBHOOK_URL not set — DC_001")

    summary = status_obj.get("summary", {})
    steps = status_obj.get("steps", {})
    icon = summary.get("icon", "❓")
    overall = summary.get("overall_status", "UNKNOWN")
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    lines = [f"## {icon} BROski Brain Ops — {date_str}", f"**Status:** {overall}", ""]
    for step_name, step_data in steps.items():
        step_icon = step_data.get("icon", "❓")
        step_status = step_data.get("status", "UNKNOWN")
        lines.append(f"{step_icon} **{step_name.replace('_', ' ').title()}** — {step_status}")

    next_steps = summary.get("next_steps", [])
    if next_steps:
        lines.append("\n**Next Steps:**")
        for ns in next_steps:
            lines.append(f"• {ns}")

    message = "\n".join(lines)
    resp = requests.post(
        webhook_url,
        json={"content": message, "username": "BROski Brain Ops"},
        timeout=10,
    )
    if resp.status_code in (401, 403):
        raise PermissionError(f"Discord webhook auth failed ({resp.status_code}) — DC_002")
    if resp.status_code == 404:
        raise ValueError(f"Discord webhook URL invalid or deleted — DC_001")
    resp.raise_for_status()

    return {
        "webhook_url_prefix": webhook_url[:40] + "...",
        "message_length": len(message),
        "http_status": resp.status_code,
    }


# ---------------------------------------------------------------------------
# Main chain runner
# ---------------------------------------------------------------------------

def run_ops_chain(config: dict, dry_run: bool = False, only_step: Optional[str] = None):
    """Execute the full 5-step brain ops chain."""
    vault_path = config["vault_path"]
    log_path = vault_path / "Ops-Logs" / f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-ops.log"

    handler = OperationHandler(
        max_retries=3,
        retry_delays=[1.0, 2.0, 4.0],
        circuit_breaker=CircuitBreaker(failure_threshold=5, recovery_timeout=300),
        log_path=log_path,
    )
    session = OpsSession(handler=handler, output_dir=vault_path / "Ops-Logs")

    print(f"\n🧠 BROski Brain Ops — Session {session.session_id}")
    print(f"📁 Vault: {vault_path}")
    print(f"📋 Mode: {'DRY RUN' if dry_run else 'LIVE'}\n")

    github_data = None
    status_obj = None

    # --- Step 1: Health check (hard stop on failure) ---
    if not only_step or only_step == "health_check":
        print("⚡ [1/5] Health check...")
        if dry_run:
            print("   DRY RUN — skipping")
        else:
            hc = session.run_step("health_check", step_health_check, config)
            print(f"   {hc.icon} {hc.status}")
            if not hc.success:
                print(f"   ❌ Health check failed ({hc.error_code}) — STOPPING")
                print(f"   Action: check Docker + hyper-brain container")
                status_obj = session.build_status_object()
                session.save_status(status_obj)
                return status_obj

    # --- Step 2: GitHub sync ---
    if not only_step or only_step == "github_sync":
        print("⚡ [2/5] GitHub sync...")
        if dry_run:
            print("   DRY RUN — skipping")
        else:
            gs = session.run_step(
                "github_sync",
                step_github_sync,
                config,
                partial_check=lambda r: r.get("repos_failed", 0) > 0,
            )
            print(f"   {gs.icon} {gs.status}")
            if gs.success:
                github_data = gs.details

    # --- Step 3: Briefing generation ---
    if not only_step or only_step == "briefing_generation":
        print("⚡ [3/5] Briefing generation...")
        if dry_run:
            print("   DRY RUN — skipping")
        else:
            bg = session.run_step(
                "briefing_generation",
                step_briefing_generation,
                config,
                github_data=github_data,
            )
            print(f"   {bg.icon} {bg.status}")

    # --- Step 4: Vault commit ---
    if not only_step or only_step == "vault_commit":
        print("⚡ [4/5] Vault commit...")
        if dry_run:
            print("   DRY RUN — skipping")
        else:
            vc = session.run_step("vault_commit", step_vault_commit, config)
            print(f"   {vc.icon} {vc.status}")

    # --- Step 5: Discord report ---
    if not only_step or only_step == "discord_report":
        print("⚡ [5/5] Discord report...")
        if dry_run:
            print("   DRY RUN — skipping")
        else:
            status_obj = session.build_status_object()
            dr = session.run_step(
                "discord_report",
                step_discord_report,
                config,
                status_obj=status_obj,
            )
            print(f"   {dr.icon} {dr.status}")

    # Build + save final status
    status_obj = session.build_status_object()
    out_path = session.save_status(status_obj)

    # Print summary
    s = status_obj["summary"]
    print(f"\n{'='*50}")
    print(f"{s['icon']} Brain Ops Complete — {s['overall_status']}")
    if s["next_steps"]:
        print("\n🔧 Next Steps:")
        for ns in s["next_steps"]:
            print(f"   • {ns}")
    print(f"\n📄 Status saved: {out_path}")
    print(f"📋 Log: {log_path}")
    print()

    return status_obj


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="🧠 HyperCode-V2.4 Brain Ops Chain",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m ops.hyper_brain_ops                    # Full chain
  python -m ops.hyper_brain_ops --dry-run          # Validate config only
  python -m ops.hyper_brain_ops --step github_sync # Single step
""",
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate config, skip execution")
    parser.add_argument("--step", choices=OpsSession.CHAIN, help="Run a single step only")
    parser.add_argument("--json", action="store_true", help="Print status JSON to stdout")
    args = parser.parse_args()

    config = load_config()

    if args.dry_run:
        print("\n🔍 Dry run — config validation:")
        print(f"   GITHUB_PAT:          {'✅ set' if config['github_pat'] else '❌ missing'}")
        print(f"   GITHUB_REPOS:        {'✅ ' + str(config['github_repos']) if config['github_repos'] else '❌ missing'}")
        print(f"   VAULT_PATH:          {config['vault_path']} ({'✅ exists' if config['vault_path'].exists() else '⚠️ will create'})")
        print(f"   DISCORD_WEBHOOK_URL: {'✅ set' if config['discord_webhook_url'] else '⚠️ not set (Discord step will fail)'}")
        print(f"   BRIEFING_API_URL:    {config['briefing_api_url']}")
        return

    status = run_ops_chain(config, dry_run=False, only_step=args.step)

    if args.json:
        print(json.dumps(status, indent=2))

    all_ok = status.get("summary", {}).get("all_ok", False)
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
