#!/usr/bin/env python3
"""
hfz_ecosystem.py — HyperFocus Z0ne Ecosystem Health Board
Runs session_start + env_guard across all 14 repos and prints one green/red board.

Usage:
    python scripts/hfz_ecosystem.py
    python scripts/hfz_ecosystem.py --env-only
    python scripts/hfz_ecosystem.py --repo HyperCode-V2.4
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

# ——— CONFIG ———
WORKSPACE = Path(r"H:\HYPERFOCUSZONE\HperCore")

REPOS = [
    {"name": "HyperCode-V2.4",                                "canonical": True},
    {"name": "THE-HYPERCODE",                                  "canonical": False, "note": "V3 experimental"},
    {"name": "Hyper-Vibe-Coding-Course",                       "canonical": True},
    {"name": "HyperAgent-SDK",                                 "canonical": True},
    {"name": "BROskiPets-LLM-dNFT",                           "canonical": True},
    {"name": "BROski-Obsidian-Brain-for-HyperFocus-z0ne",      "canonical": True},
    {"name": "hyper-agents-ide",                               "canonical": True},
    {"name": "showcase-web",                                   "canonical": True},
    {"name": "HYPER-SILLs-By-WelshDog",                       "canonical": True},
    {"name": "Hyper-Docker",                                   "canonical": True},
    {"name": "WelshDog-Mission-Control",                       "canonical": True},
    {"name": "welshdog-designs-web3-shop",                     "canonical": True},
    {"name": "hyperfocuszone.com-Support-Hub-",                "canonical": True},
    {"name": "trae-ide",                                       "canonical": False, "note": "local IDE state"},
]

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
DIM    = "\033[2m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def find_hook(hooks_dir: Path, pattern: str) -> Optional[Path]:
    """Glob for a hook script matching pattern. Returns first match or None."""
    matches = list(hooks_dir.glob(f"*{pattern}*.py"))
    return matches[0] if matches else None


def run_script(script_path: Path, timeout: int = 15) -> tuple[bool, str]:
    """Run a hook script. Returns (success, output)."""
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True, text=True, timeout=timeout,
            cwd=script_path.parent.parent.parent  # repo root (hooks/ -> .claude/ -> root)
        )
        output = (result.stdout + result.stderr).strip()
        return result.returncode == 0, output
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT"
    except Exception as e:
        return False, str(e)


def check_repo(repo: dict, env_only: bool = False) -> dict:
    repo_path = WORKSPACE / repo["name"]
    hooks_dir = repo_path / ".claude" / "hooks"

    result = {
        "name": repo["name"],
        "exists": repo_path.exists(),
        "is_git": (repo_path / ".git").exists(),
        "canonical": repo.get("canonical", True),
        "note": repo.get("note", ""),
        "hooks_exist": hooks_dir.exists(),
        "session_start": None,
        "env_guard": None,
        "session_start_out": "",
        "env_guard_out": "",
    }

    if not result["exists"] or not result["hooks_exist"]:
        return result

    # Auto-discover by glob — no hard-coded prefixes
    env_script     = find_hook(hooks_dir, "env_guard")
    session_script = find_hook(hooks_dir, "session_start")

    if env_script:
        ok, out = run_script(env_script)
        result["env_guard"] = ok
        result["env_guard_out"] = out[:200]
    else:
        result["env_guard"] = False
        result["env_guard_out"] = f"no *env_guard*.py found in {hooks_dir}"

    if not env_only:
        if session_script:
            ok, out = run_script(session_script)
            result["session_start"] = ok
            result["session_start_out"] = out[:200]
        else:
            result["session_start"] = False
            result["session_start_out"] = f"no *session_start*.py found in {hooks_dir}"

    return result


def status_icon(value: Optional[bool], exists: bool, hooks_exist: bool) -> str:
    if not exists:
        return f"{DIM}\u2501\u2501 MISSING{RESET}"
    if not hooks_exist:
        return f"{YELLOW}\u26a0\ufe0f NO HOOKS{RESET}"
    if value is None:
        return f"{DIM}-- SKIP  {RESET}"
    return f"{GREEN}\u2705 OK    {RESET}" if value else f"{RED}\u274c FAIL  {RESET}"


def print_board(results: list, elapsed: float, env_only: bool):
    width = 62
    print()
    print(f"{BOLD}{'=' * width}{RESET}")
    print(f"{BOLD}  \U0001f43e HyperFocus Z0ne \u2014 Ecosystem Health Board{RESET}")
    print(f"{DIM}  {time.strftime('%Y-%m-%d %H:%M:%S')} \u00b7 {elapsed:.1f}s{RESET}")
    print(f"{'=' * width}{RESET}")

    col_session = " SESSION " if not env_only else ""
    print(f"  {'REPO':<42} {'ENV':^9}{col_session:^9}")
    print(f"  {'-' * 42} {'---------'} {'---------'}")

    total_ok = 0
    total_checks = 0

    for r in results:
        tag = f" {DIM}[{r['note']}]{RESET}" if r["note"] else ""
        name = r["name"][:40]
        env_s  = status_icon(r["env_guard"],    r["exists"], r["hooks_exist"])
        sess_s = status_icon(r["session_start"], r["exists"], r["hooks_exist"]) if not env_only else ""
        print(f"  {name:<42} {env_s} {sess_s}{tag}")

        for check in [r["env_guard"], r["session_start"]]:
            if check is not None:
                total_checks += 1
                if check:
                    total_ok += 1

    print(f"{'=' * width}")
    score_color = GREEN if total_ok == total_checks else (YELLOW if total_ok >= total_checks * 0.8 else RED)
    print(f"{score_color}{BOLD}  Score: {total_ok}/{total_checks} checks passed{RESET}")

    failures = [
        r for r in results
        if r["env_guard"] is False or r["session_start"] is False
    ]
    if failures:
        print(f"\n{RED}{BOLD}  Failures:{RESET}")
        for r in failures:
            if r["env_guard"] is False:
                print(f"  {RED}\u2022{RESET} {r['name']} env_guard: {DIM}{r['env_guard_out'][:120]}{RESET}")
            if r["session_start"] is False:
                print(f"  {RED}\u2022{RESET} {r['name']} session_start: {DIM}{r['session_start_out'][:120]}{RESET}")
    else:
        print(f"{GREEN}  All checks passed \U0001f680{RESET}")

    print(f"{'=' * width}")
    print()


def main():
    parser = argparse.ArgumentParser(description="HyperFocus Z0ne Ecosystem Health Board")
    parser.add_argument("--env-only", action="store_true", help="Run env_guard only (faster)")
    parser.add_argument("--repo",     type=str,            help="Check a single repo by name")
    args = parser.parse_args()

    repos_to_check = REPOS
    if args.repo:
        repos_to_check = [r for r in REPOS if r["name"].lower() == args.repo.lower()]
        if not repos_to_check:
            print(f"{RED}Repo '{args.repo}' not found in REPOS list.{RESET}")
            sys.exit(1)

    print(f"{DIM}Scanning {len(repos_to_check)} repo(s)...{RESET}")
    t_start = time.time()
    results = [check_repo(r, env_only=args.env_only) for r in repos_to_check]
    elapsed = time.time() - t_start

    print_board(results, elapsed, args.env_only)

    any_fail = any(
        r["env_guard"] is False or r["session_start"] is False
        for r in results
    )
    sys.exit(1 if any_fail else 0)


if __name__ == "__main__":
    main()
