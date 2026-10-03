#!/usr/bin/env python3
"""Rotate HyperCode's JWT signing secret, safely and without ever printing a secret.

Why this exists: the 10-year admin token in .env (DASHBOARD_SERVICE_JWT) was exposed in a transcript on 2026-10-03.
Anyone holding it can act as that admin until the SIGNING secret changes. Core signs/verifies with
HYPERCODE_JWT_SECRET (compose maps it to JWT_SECRET); secrets/jwt_secret.txt is kept in sync with it.

What it does (stop at the first failure, nothing is printed except 8-char hash prefixes, names and HTTP codes):
  1. preflight  : RAM guard GREEN, core healthy, .env / secrets file / live core all agree on the OLD secret
  2. backup     : .env, secrets/jwt_secret.txt, secrets/dashboard_service_jwt.txt -> *.bak-jwt-rotation-<ts> (gitignored)
  3. write      : new 64-hex secret -> .env HYPERCODE_JWT_SECRET + secrets/jwt_secret.txt; DASHBOARD_SERVICE_JWT line removed
  4. restart    : every running container that holds the old secret (found by hash), core first, wait healthy
  5. re-mint    : new 30-day dashboard service JWT (same subject as the old one) -> secrets/dashboard_service_jwt.txt,
                  restart the dashboard (it caches the token in memory)
  6. verify     : old 10-year token + old 30-day token are REJECTED, new token accepted, dashboard /api/pulse OK,
                  no container still holds the old secret, core RestartCount 0

Usage (from HyperCode-V2.4/, Git Bash):   MSYS_NO_PATHCONV=1 python scripts/rotate_jwt_secret.py --yes
Side effects to expect: every existing login/session token (and any agent that minted its own JWT) stops working and
must log in again. Run when no crew run is in flight.
Rollback: copy the three *.bak-jwt-rotation-<ts> files back over their originals, restart the consumers it listed.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import secrets as pysecrets
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ENV_KEY = "HYPERCODE_JWT_SECRET"
DASH_KEY = "DASHBOARD_SERVICE_JWT"
SECRET_VARS = ("JWT_SECRET", "HYPERCODE_JWT_SECRET")
SECRET_FILE_VARS = ("JWT_SECRET_FILE", "HYPERCODE_JWT_SECRET_FILE")
# Data stores get the whole .env via `env_file:` but never use the JWT secret: not worth a database restart.
LEAVE_RUNNING = {"postgres", "redis"}


# --- pure helpers (unit-tested; no I/O) -------------------------------------------------------------------------
def sha8(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:8]


def get_env_value(text: str, key: str) -> str | None:
    m = re.search(rf"^{re.escape(key)}=(.*?)\r?$", text, re.M)
    return m.group(1).strip().strip('"').strip("'") if m else None


def replace_env_line(text: str, key: str, value: str) -> str:
    """Replace `key=...` (exactly one line) keeping the file's own line endings. Raises if not exactly one."""
    pat = re.compile(rf"^{re.escape(key)}=.*?(\r?)$", re.M)
    if len(pat.findall(text)) != 1:
        raise ValueError(f"{key} must appear exactly once")
    return pat.sub(lambda m: f"{key}={value}{m.group(1)}", text, count=1)


def drop_env_line(text: str, key: str) -> str:
    """Remove the whole `key=...` line (and its newline). No-op when absent."""
    return re.sub(rf"^{re.escape(key)}=.*?(\r?\n|$)", "", text, count=1, flags=re.M)


def jwt_claims(token: str) -> dict:
    """Decode a JWT's payload WITHOUT verifying it (we only need sub/iss/aud/exp of our own old token)."""
    part = token.split(".")[1]
    part += "=" * (-len(part) % 4)
    return json.loads(base64.urlsafe_b64decode(part))


# --- shell helpers ----------------------------------------------------------------------------------------------
def run(args, input_text=None, check=True):
    r = subprocess.run(args, input=input_text, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise SystemExit(f"command failed ({r.returncode}): {' '.join(args[:4])} ... {r.stderr.strip()[:200]}")
    return r


def container_env(name: str) -> dict[str, str]:
    out = run(["docker", "inspect", "-f", "{{range .Config.Env}}{{println .}}{{end}}", name]).stdout
    return dict(ln.split("=", 1) for ln in out.splitlines() if "=" in ln)


def consumers(old_hash: str) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """(by_env, by_file): (container, compose service) pairs that hold the old secret / read a *_FILE secret."""
    by_env, by_file = [], []
    for name in run(["docker", "ps", "--format", "{{.Names}}"]).stdout.split():
        env = container_env(name)
        svc = run(["docker", "inspect", "-f", '{{index .Config.Labels "com.docker.compose.service"}}', name]).stdout.strip()
        if any(env.get(k) and sha8(env[k]) == old_hash for k in SECRET_VARS):
            by_env.append((name, svc))
        elif any(env.get(k) for k in SECRET_FILE_VARS):
            by_file.append((name, svc))
    return by_env, by_file


def wait_healthy(name: str, tries: int = 5, gap: int = 30) -> bool:
    for _ in range(tries):
        st = run(["docker", "inspect", "-f", "{{.State.Health.Status}}", name], check=False).stdout.strip()
        if st == "healthy":
            return True
        time.sleep(gap)
    return False


CHECK_CODE = (
    "import sys,urllib.request,urllib.error\n"
    "tok=sys.stdin.read().strip()\n"
    "rq=urllib.request.Request('http://localhost:8000/api/v1/orchestrator/agents',headers={'Authorization':'Bearer '+tok})\n"
    "try:\n    print(urllib.request.urlopen(rq,timeout=15).status)\n"
    "except urllib.error.HTTPError as e:\n    print(e.code)\n"
)


def token_status(token: str) -> str:
    """HTTP status core gives this token on an authenticated route (token goes via stdin, never argv)."""
    return run(["docker", "exec", "-i", "hypercode-core", "python", "-c", CHECK_CODE], input_text=token, check=False).stdout.strip()


# --- main -------------------------------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true", help="really rotate (without it: preflight only, nothing written)")
    args = ap.parse_args()
    root = Path.cwd()
    env_path, jwt_path, dash_path = root / ".env", root / "secrets/jwt_secret.txt", root / "secrets/dashboard_service_jwt.txt"
    for p in (env_path, jwt_path, dash_path, root / "scripts/ram_guard.py"):
        if not p.exists():
            raise SystemExit(f"run me from HyperCode-V2.4/ (missing {p})")

    print("== 1. preflight")
    g = run([sys.executable, "scripts/ram_guard.py", "--for", "build"], check=False)
    print("  RAM guard:", "GREEN" if g.returncode == 0 else f"NOT green (exit {g.returncode}) - stop, free memory first")
    if g.returncode != 0:
        return 2
    if run(["docker", "inspect", "-f", "{{.State.Health.Status}}", "hypercode-core"]).stdout.strip() != "healthy":
        raise SystemExit("core is not healthy - stop")
    env_text = env_path.read_text(encoding="utf-8", newline="")
    old = get_env_value(env_text, ENV_KEY)
    old_file = jwt_path.read_text(encoding="utf-8").strip()
    live = container_env("hypercode-core").get("JWT_SECRET", "")
    print(f"  old secret hashes  .env:{sha8(old or '')}  secrets/jwt_secret.txt:{sha8(old_file)}  live core:{sha8(live)}")
    if not old or not (old == old_file == live):
        raise SystemExit("the three sources do NOT agree - stop (nothing was changed)")
    old_hash = sha8(old)
    old_dash_env = get_env_value(env_text, DASH_KEY)
    old_dash_file = dash_path.read_text(encoding="utf-8").strip()
    claims = jwt_claims(old_dash_file)
    print(f"  old dashboard token: sub={claims.get('sub')} has iss={'iss' in claims} aud={'aud' in claims}"
          f" exp={datetime.fromtimestamp(claims['exp']).date()}; 10-year .env token present: {bool(old_dash_env)}")
    by_env, by_file = consumers(old_hash)
    left = [n for n, s_ in by_env if s_ in LEAVE_RUNNING]
    by_env = [t for t in by_env if t[1] not in LEAVE_RUNNING]
    print("  holds old secret (env) -> will restart:", [n for n, _ in by_env] or "none")
    print("  holds a copy via env_file, does NOT use it -> left running:", left or "none")
    print("  reads a secret file   :", [n for n, _ in by_file] or "none")
    if not any(n == "hypercode-core" for n, _ in by_env):
        raise SystemExit("hypercode-core is not among the consumers - unexpected, stop")
    if not args.yes:
        print("\nPreflight OK. Nothing written. Re-run with --yes to rotate.")
        return 0

    print("== 2. backup")
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    for p in (env_path, jwt_path, dash_path):
        b = p.with_name(p.name + f".bak-jwt-rotation-{ts}")
        b.write_bytes(p.read_bytes())
        print("  ", b.relative_to(root))

    print("== 3. write new secret")
    new = pysecrets.token_hex(32)
    new_env = drop_env_line(replace_env_line(env_text, ENV_KEY, new), DASH_KEY)
    env_path.write_text(new_env, encoding="utf-8", newline="")
    jwt_path.write_text(new, encoding="utf-8", newline="")
    print(f"  new secret hash {sha8(new)}; {DASH_KEY} line removed from .env")

    print("== 4. restart consumers (core first)")
    order = sorted(by_env, key=lambda t: t[0] != "hypercode-core")
    for name, svc in order:
        r = run(["docker", "compose", "up", "-d", "--no-deps", svc], check=False)
        print(f"  {svc}: compose up exit {r.returncode}")
        if r.returncode != 0:
            print("  STOP. Restore the backups (see header) and restart this service.", r.stderr.strip()[:200])
            return 3
        if not wait_healthy(name):
            print(f"  STOP: {name} not healthy after 5 x 30 s")
            return 3
    for name, svc in by_file:
        run(["docker", "restart", name])
        print(f"  {svc}: restarted (reads the secret file)")
        if not wait_healthy(name):
            print(f"  STOP: {name} not healthy after 5 x 30 s")
            return 3

    print("== 5. re-mint the dashboard token (30 days, same subject)")
    code = ("from datetime import timedelta; from app.core.security import create_access_token;"
            f"print(create_access_token({str(claims['sub'])!r}, timedelta(days=30)))")
    tok = run(["docker", "exec", "hypercode-core", "python", "-c", code]).stdout.strip()
    if tok.count(".") != 2:
        raise SystemExit("mint failed - the OLD dashboard token file is still backed up, restore it")
    dash_path.write_text(tok, encoding="utf-8", newline="")
    run(["docker", "restart", "hypercode-dashboard"])
    wait_healthy("hypercode-dashboard")
    print(f"  new dashboard token written (exp {datetime.fromtimestamp(jwt_claims(tok)['exp']).date()})")

    print("== 6. verify")
    results = {
        "new token accepted by core (want 200)": token_status(tok),
        "old 30-day token rejected (want 401/403)": token_status(old_dash_file),
        "old 10-year token rejected (want 401/403)": token_status(old_dash_env) if old_dash_env else "n/a (not present)",
    }
    time.sleep(5)
    try:
        import urllib.request
        pulse = json.loads(urllib.request.urlopen("http://127.0.0.1:8088/api/pulse", timeout=20).read())
        results["dashboard /api/pulse healthy (want True)"] = str("degraded" not in pulse)
    except Exception as e:  # noqa: BLE001 - report, don't hide
        results["dashboard /api/pulse healthy (want True)"] = f"error: {type(e).__name__}"
    still = [n for n, s_ in consumers(old_hash)[0] if s_ not in LEAVE_RUNNING]
    results["containers still holding the old secret (want [])"] = str(still)
    results["core RestartCount (want 0)"] = run(["docker", "inspect", "-f", "{{.RestartCount}}", "hypercode-core"]).stdout.strip()
    for k, v in results.items():
        print(f"  {k}: {v}")
    ok = (results["new token accepted by core (want 200)"] == "200"
          and results["old 30-day token rejected (want 401/403)"] in ("401", "403")
          and results["old 10-year token rejected (want 401/403)"] in ("401", "403", "n/a (not present)")
          and not still)
    print("\nRESULT:", "ROTATED + VERIFIED" if ok else "CHECK THE LINES ABOVE - not all green")
    return 0 if ok else 4


if __name__ == "__main__":
    sys.exit(main())
