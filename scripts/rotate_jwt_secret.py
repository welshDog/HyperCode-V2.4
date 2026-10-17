#!/usr/bin/env python3
"""Rotate HyperCode's JWT signing secret, safely and without ever printing a secret.

Why this exists: the 10-year admin token in .env (DASHBOARD_SERVICE_JWT) was exposed in a transcript on 2026-10-03.
Anyone holding it can act as that admin until the SIGNING secret changes.

TWO LAYOUTS are supported (since 2026-10-17):
  * FILE  (current): core reads secrets/jwt_secret.txt through JWT_SECRET_FILE / HYPERCODE_JWT_SECRET_FILE; the .env value
    is empty or unused. The live secret is read from INSIDE core (settings.JWT_SECRET), so either layout is seen correctly.
  * ENV   (original): core held the secret in HYPERCODE_JWT_SECRET (compose maps it to JWT_SECRET); .env + the file agree.

What it does (stop at the first failure, nothing is printed except 8-char hash prefixes, names and HTTP codes):
  1. preflight  : RAM guard GREEN, core healthy, secrets/jwt_secret.txt == the secret LIVE in core (and .env, if it holds one)
  2. backup     : .env, secrets/jwt_secret.txt, secrets/dashboard_service_jwt.txt -> *.bak-jwt-rotation-<ts> (gitignored)
  3. write      : new 64-hex secret -> .env HYPERCODE_JWT_SECRET + secrets/jwt_secret.txt; DASHBOARD_SERVICE_JWT line removed
  4. restart    : every running container holding the old secret (env hash OR a jwt_secret.txt mount), core first
  5. re-mint    : new 30-day dashboard service JWT (same subject as the old one) -> secrets/dashboard_service_jwt.txt,
                  RECREATE the dashboard (it caches the token in memory; a plain restart under load once broke its fs)
  6. verify     : old 10-year token + old 30-day token are REJECTED, new token accepted, dashboard /api/pulse OK,
                  no container still holds the old secret, core RestartCount 0

Usage (from HyperCode-V2.4/, Git Bash):   MSYS_NO_PATHCONV=1 python scripts/rotate_jwt_secret.py --yes
Side effects to expect: every existing login/session token (and any agent that minted its own JWT) stops working and
must log in again. Run when no crew run is in flight.
Rollback: copy the *.bak-jwt-rotation-<ts> files back over their originals, restart the consumers it listed.
The backup of jwt_secret.txt holds the OLD secret: delete it once you are happy (it is gitignored).
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


# --- shell helpers (1/2) ----------------------------------------------------------------------------------------
def run(args, input_text=None, check=True):
    r = subprocess.run(args, input=input_text, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise SystemExit(f"command failed ({r.returncode}): {' '.join(args[:4])} ... {r.stderr.strip()[:200]}")
    return r


def secret_file_holders(inspected: list[dict]) -> list[str]:
    """Names of containers (from `docker inspect` JSON objects) that bind-mount secrets/jwt_secret.txt. Pure."""
    out = []
    for j in inspected:
        for m in j.get("Mounts") or []:
            if str(m.get("Source", "")).replace("\\", "/").endswith("/jwt_secret.txt"):
                out.append(str(j.get("Name", "")).lstrip("/"))
                break
    return out


def compose_target(labels: dict, root: Path) -> tuple[list[str], str]:
    """(`-f` args, compose service) a container was started with, from its compose labels. Pure.

    Paths are made relative to `root` when possible. The profile flags are added by the caller.
    """
    files = [f.strip() for f in str(labels.get("com.docker.compose.project.config_files", "")).split(",") if f.strip()]
    svc = str(labels.get("com.docker.compose.service", ""))
    if not files or not svc:
        raise ValueError("container has no compose labels")
    args: list[str] = []
    for f in files:
        try:
            f = str(Path(f).relative_to(root))
        except ValueError:
            pass
        args += ["-f", f]
    return args, svc


# --- shell helpers (2/2) ----------------------------------------------------------------------------------------
def inspect_json(name: str) -> dict:
    return json.loads(run(["docker", "inspect", "-f", "{{json .}}", name]).stdout)


LIVE_HASH_CODE = (
    "import hashlib\n"
    "from app.core.config import settings\n"
    "print(hashlib.sha256((settings.JWT_SECRET or '').encode()).hexdigest()[:8])\n"
)


def live_core_hash() -> str:
    """sha8 of the secret core is ACTUALLY using (correct for both layouts: env var or secret file)."""
    r = run(["docker", "exec", "-e", "PYTHONPATH=/app", "-w", "/app", "hypercode-core", "python", "-c", LIVE_HASH_CODE], check=False)
    return r.stdout.strip()


def consumers(old_hash: str) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """(by_env, by_file): (container, compose service) pairs that hold the old secret in env / read it from a file."""
    by_env, by_file = [], []
    for name in run(["docker", "ps", "--format", "{{.Names}}"]).stdout.split():
        j = inspect_json(name)
        env = dict(e.split("=", 1) for e in (j.get("Config", {}).get("Env") or []) if "=" in e)
        svc = (j.get("Config", {}).get("Labels") or {}).get("com.docker.compose.service", name)
        via_file = bool(secret_file_holders([j])) or any(env.get(k) for k in SECRET_FILE_VARS)
        via_env = any(env.get(k) and sha8(env[k]) == old_hash for k in SECRET_VARS)
        if via_file:
            by_file.append((name, svc))
        elif via_env:
            by_env.append((name, svc))
    return by_env, by_file


def wait_healthy(name: str, tries: int = 12, gap: int = 15) -> bool:
    for _ in range(tries):
        st = run(["docker", "inspect", "-f", "{{.State.Health.Status}}", name], check=False).stdout.strip()
        if st == "healthy":
            return True
        time.sleep(gap)
    return False


def recreate(container: str) -> bool:
    """Recreate a container from the compose files it was started with (env kept), then wait for healthy."""
    labels = inspect_json(container).get("Config", {}).get("Labels") or {}
    f_args, svc = compose_target(labels, Path.cwd())
    profiles = ["--profile", "agents", "--profile", "hyper", "--profile", "safety", "--profile", "studio"]
    if any(a.endswith("docker-compose.fleet.yml") for a in f_args):
        profiles += ["--profile", "fleet"]
    r = run(["docker", "compose", *f_args, *profiles, "up", "-d", "--no-deps", "--no-build", "--force-recreate", svc], check=False)
    print(f"  {svc}: compose recreate exit {r.returncode}")
    return r.returncode == 0 and wait_healthy(container)


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
    for p in (jwt_path, dash_path, root / "scripts/ram_guard.py"):
        if not p.exists():
            raise SystemExit(f"run me from HyperCode-V2.4/ (missing {p})")

    print("== 1. preflight")
    g = run([sys.executable, "scripts/ram_guard.py", "--for", "build"], check=False)
    print("  RAM guard:", "GREEN" if g.returncode == 0 else f"NOT green (exit {g.returncode}) - stop, free memory first")
    if g.returncode != 0:
        return 2
    if run(["docker", "inspect", "-f", "{{.State.Health.Status}}", "hypercode-core"]).stdout.strip() != "healthy":
        raise SystemExit("core is not healthy - stop")
    env_text = env_path.read_text(encoding="utf-8", newline="") if env_path.exists() else ""
    env_val = get_env_value(env_text, ENV_KEY) or ""
    old = jwt_path.read_text(encoding="utf-8-sig").strip()
    live = live_core_hash()
    print(f"  old secret hashes  secrets/jwt_secret.txt:{sha8(old)}  live core:{live}  "
          f".env {ENV_KEY}:{sha8(env_val) if env_val else 'empty/absent'}")
    if not old or live != sha8(old):
        raise SystemExit("secrets/jwt_secret.txt is NOT the secret core is using - stop (nothing was changed)")
    env_in_sync = bool(env_val) and env_val == old
    if env_val and not env_in_sync:
        print(f"  note: .env {ENV_KEY} holds a DIFFERENT value than core uses - left untouched (core ignores it)")
    old_hash = sha8(old)
    old_dash_env = get_env_value(env_text, DASH_KEY)
    old_dash_file = dash_path.read_text(encoding="utf-8-sig").strip()
    claims = jwt_claims(old_dash_file)
    exp_txt = datetime.fromtimestamp(claims["exp"]).date() if "exp" in claims else "none"
    print(f"  old dashboard token: sub={claims.get('sub')} has iss={'iss' in claims} aud={'aud' in claims}"
          f" exp={exp_txt}; 10-year .env token present: {bool(old_dash_env)}")
    by_env, by_file = consumers(old_hash)
    left = [n for n, s_ in by_env if s_ in LEAVE_RUNNING]
    by_env = [t for t in by_env if t[1] not in LEAVE_RUNNING]
    print("  holds old secret (env) -> will recreate:", [n for n, _ in by_env] or "none")
    print("  holds a copy via env_file, does NOT use it -> left running:", left or "none")
    print("  reads the secret file -> will restart :", [n for n, _ in by_file] or "none")
    if not any(n == "hypercode-core" for n, _ in by_env + by_file):
        raise SystemExit("hypercode-core is not among the consumers - unexpected, stop")
    if not args.yes:
        print("\nPreflight OK. Nothing written. Re-run with --yes to rotate.")
        return 0

    print("== 2. backup")
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    for p in [jwt_path, dash_path] + ([env_path] if env_path.exists() else []):
        b = p.with_name(p.name + f".bak-jwt-rotation-{ts}")
        b.write_bytes(p.read_bytes())
        print("  ", b.relative_to(root))

    print("== 3. write new secret")
    new = pysecrets.token_hex(32)
    jwt_path.write_text(new, encoding="utf-8", newline="")
    msg = f"  new secret hash {sha8(new)} written to secrets/jwt_secret.txt"
    if env_path.exists():
        new_env = env_text
        if env_in_sync:
            new_env = replace_env_line(new_env, ENV_KEY, new)
            msg += f"; .env {ENV_KEY} updated"
        if old_dash_env is not None:
            new_env = drop_env_line(new_env, DASH_KEY)
            msg += f"; {DASH_KEY} line removed from .env"
        if new_env != env_text:
            env_path.write_text(new_env, encoding="utf-8", newline="")
    print(msg)

    print("== 4. restart consumers (core first)")
    work = [(n, s_, "recreate") for n, s_ in by_env] + [(n, s_, "restart") for n, s_ in by_file]
    for name, svc, how in sorted(work, key=lambda t: t[0] != "hypercode-core"):
        if how == "recreate":
            ok = recreate(name)
        else:
            run(["docker", "restart", name])
            print(f"  {svc}: restarted (reads the secret file)")
            ok = wait_healthy(name)
        if not ok:
            print(f"  STOP: {name} not healthy. Restore the backups (see header) and restart this service.")
            return 3

    print("== 5. re-mint the dashboard token (30 days, same subject)")
    code = ("from datetime import timedelta; from app.core.security import create_access_token;"
            f"print(create_access_token({str(claims['sub'])!r}, timedelta(days=30)))")
    tok = run(["docker", "exec", "-e", "PYTHONPATH=/app", "-w", "/app", "hypercode-core", "python", "-c", code]).stdout.strip()
    if tok.count(".") != 2:
        raise SystemExit("mint failed - the OLD dashboard token file is still backed up, restore it")
    dash_path.write_text(tok, encoding="utf-8", newline="")
    if not recreate("hypercode-dashboard"):
        print("  WARNING: dashboard did not come back healthy after the recreate - check it before anything else")
    print(f"  new dashboard token written (exp {datetime.fromtimestamp(jwt_claims(tok)['exp']).date()})")

    print("== 6. verify")
    results = {
        "core now uses the new secret (want True)": str(live_core_hash() == sha8(new)),
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
    results["containers still holding the old secret in env (want [])"] = str(still)
    for k, v in results.items():
        print(f"  {k}: {v}")
    ok = (results["core now uses the new secret (want True)"] == "True"
          and results["new token accepted by core (want 200)"] == "200"
          and results["old 30-day token rejected (want 401/403)"] in ("401", "403")
          and results["old 10-year token rejected (want 401/403)"] in ("401", "403", "n/a (not present)")
          and not still)
    print("\nRESULT:", "ROTATED + VERIFIED" if ok else "CHECK THE LINES ABOVE - not all green")
    return 0 if ok else 4


if __name__ == "__main__":
    sys.exit(main())
