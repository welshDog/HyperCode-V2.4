#!/usr/bin/env python3
"""READ-ONLY full-stack test for HyperCode V2.4: host, containers, data stores, backups, security, apps, CI, unit tests.

Nothing is changed and no secret is ever printed (keys are only sent as headers and compared by HTTP status). Needs: docker, git,
gh (for the CI section), PowerShell. Run from HyperCode-V2.4/:   python scripts/full_system_test.py [--json out.json] [--skip-tests] [--skip-auth]
Exit code: 0 = no FAIL, 1 = at least one FAIL.  Statuses: PASS, WARN (works but needs a look), FAIL (broken), INFO (context).
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R: list[dict] = []


def rec(area: str, name: str, status: str, detail: str = "") -> None:
    R.append({"area": area, "name": name, "status": status, "detail": detail})
    mark = {"PASS": "ok  ", "WARN": "WARN", "FAIL": "FAIL", "INFO": "info"}[status]
    print(f"  [{mark}] {name}" + (f"  -  {detail}" if detail else ""), flush=True)


def sh(args, timeout=60, cwd=None, inp=None):
    try:
        r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout,
                           cwd=str(cwd or ROOT), input=inp)
        return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    except FileNotFoundError as e:
        return 127, "", str(e)


def ps(script: str, timeout=60):
    return sh(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script], timeout=timeout)


def docker(args, timeout=60):
    return sh(["docker", *args], timeout=timeout)


def net(py: str, *argv: str, timeout=90) -> str:
    """Run a python snippet INSIDE celery-worker (it has python and sits on the stack's networks); returns stdout."""
    b = base64.b64encode(py.encode()).decode()
    code, out, err = docker(["exec", "celery-worker", "sh", "-c", f"echo {b} | base64 -d > /tmp/_t.py && python /tmp/_t.py {' '.join(argv)}"], timeout=timeout)
    return out if code == 0 else f"ERR {code} {err[:120]}"


def read(p: str) -> str:
    return (ROOT / p).read_text(encoding="utf-8-sig").strip()


def section(title: str) -> None:
    print(f"\n== {title}", flush=True)


# ------------------------------------------------------------------------------------------------------------------
def host():
    section("1. Host and Docker engine")
    code, out, _ = ps("$o=Get-CimInstance Win32_OperatingSystem; [int]($o.FreePhysicalMemory/1KB); [int]($o.TotalVisibleMemorySize/1KB)")
    try:
        free, total = [int(x) for x in out.split()]
        rec("Host", "Windows free RAM", "FAIL" if free < 100 else "WARN" if free < 300 else "PASS", f"{free} MB free of {total} MB")
    except ValueError:
        rec("Host", "Windows free RAM", "WARN", "could not read")
    for d in ("C:\\", "H:\\"):
        u = shutil.disk_usage(d)
        gb = u.free / 2**30
        rec("Host", f"Disk {d[:2]} free", "FAIL" if gb < 10 else "WARN" if gb < 30 else "PASS", f"{gb:,.0f} GB free of {u.total / 2**30:,.0f} GB")
    try:
        shutil.disk_usage("G:\\")
        rec("Host", "Google Drive (G:) mounted", "PASS")
    except OSError:
        rec("Host", "Google Drive (G:) mounted", "FAIL", "G: does not exist: the off-site copy has nowhere to write")
    code, out, _ = sh([sys.executable, "scripts/ram_guard.py", "--for", "build"], timeout=90)
    v = re.search(r"VERDICT: (\w+)", out)
    rec("Host", "RAM guard verdict", {"GREEN": "PASS", "AMBER": "WARN"}.get(v.group(1) if v else "", "FAIL"), (v.group(0) if v else out[-80:]))
    code, out, err = sh(["wsl", "-e", "cat", "/proc/loadavg"], timeout=25)
    if code == 0 and out:
        l1 = float(out.split()[0])
        rec("Host", "WSL answers + load average", "WARN" if l1 > 8 else "PASS", f"1/5/15 min = {' / '.join(out.split()[:3])}")
    else:
        rec("Host", "WSL answers", "FAIL", f"no answer ({err[:60]})")
    code, out, err = docker(["version", "--format", "{{.Server.Version}}"], timeout=30)
    rec("Docker", "Engine answers", "PASS" if code == 0 and out else "FAIL", out or err[:80])


def containers():
    section("2. Containers")
    code, out, _ = docker(["ps", "-a", "--format", "{{.Names}}|{{.Status}}|{{.Ports}}"], timeout=60)
    rows = [l.split("|", 2) for l in out.splitlines() if "|" in l]
    running = [r for r in rows if r[1].startswith("Up")]
    exited = [r[0] for r in rows if not r[1].startswith("Up")]
    unhealthy = [r[0] for r in rows if "(unhealthy)" in r[1]]
    restarting = [r[0] for r in rows if "Restarting" in r[1]]
    rec("Containers", "Running containers", "INFO", f"{len(running)} running, {len(exited)} stopped/exited")
    rec("Containers", "No unhealthy containers", "FAIL" if unhealthy else "PASS", ", ".join(unhealthy) or "0 unhealthy")
    rec("Containers", "No restart loops", "FAIL" if restarting else "PASS", ", ".join(restarting) or "none restarting")
    if exited:
        rec("Containers", "Stopped containers", "INFO", ", ".join(exited[:14]))
    ids = [r[0] for r in running]
    code, out, _ = docker(["inspect", "--format", "{{.Name}}|{{.RestartCount}}|{{.State.OOMKilled}}", *ids], timeout=90)
    oom = [l.split("|")[0].lstrip("/") for l in out.splitlines() if l.endswith("|true")]
    restarts = sorted(((int(l.split("|")[1]), l.split("|")[0].lstrip("/")) for l in out.splitlines() if l.count("|") == 2), reverse=True)
    rec("Containers", "No OOM kills", "FAIL" if oom else "PASS", ", ".join(oom) or "none")
    busy = [f"{n} x{c}" for c, n in restarts if c > 0][:8]
    rec("Containers", "Restart counters", "WARN" if busy else "PASS", ", ".join(busy) or "all 0 since last recreate")
    code, out, _ = docker(["stats", "--no-stream", "--format", "{{.Name}}|{{.MemPerc}}|{{.CPUPerc}}"], timeout=120)
    hot = []
    for l in out.splitlines():
        p = l.split("|")
        if len(p) == 3 and p[1].endswith("%") and float(p[1][:-1]) > 85:
            hot.append(f"{p[0]} {p[1]}")
    rec("Containers", "Memory use vs limit (<85%)", "WARN" if hot else "PASS", ", ".join(hot) or "all below 85% of their limit")
    wide = [r[0] for r in rows if re.search(r"(^|, )(0\.0\.0\.0|:::)\:\d+->", r[2])]
    rec("Security", "Published ports bound to localhost only", "WARN" if wide else "PASS", ", ".join(wide) or "no 0.0.0.0 bindings")


def datastores():
    section("3. Data stores")
    def pg(q):
        c, o, e = docker(["exec", "postgres", "sh", "-c", f'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -c "{q}"'], timeout=45)
        return o if c == 0 else f"ERR {e[:80]}"
    r = pg("select 1")
    rec("Postgres", "Accepts queries", "PASS" if r == "1" else "FAIL", r)
    rec("Postgres", "Connections / DB size", "INFO", f"{pg('select count(*) from pg_stat_activity')} connections, {pg('select pg_size_pretty(pg_database_size(current_database()))')}")
    n_tables = pg("select count(*) from information_schema.tables where table_schema='public'")
    rec("Postgres", "Tables / core migration", "INFO", f"{n_tables} tables, alembic {pg('select version_num from alembic_version')}")
    w = pg("select xp||' XP, level '||level from broski_wallets where id=1")
    rec("Postgres", "BROski wallet readable", "PASS" if "XP" in w else "FAIL", w)
    rec("Postgres", "Per-agent keys minted", "INFO", f"{pg('select count(*) from agent_api_keys')} keys in agent_api_keys")
    dead = pg("select count(*) from pg_stat_activity where state='idle in transaction' and now()-state_change > interval '10 minutes'")
    rec("Postgres", "No stuck transactions", "WARN" if dead not in ("0",) else "PASS", f"{dead} idle-in-transaction > 10 min")

    def rc(*a):
        c, o, e = docker(["exec", "redis", "redis-cli", *a], timeout=30)
        return o if c == 0 else f"ERR {e[:60]}"
    rec("Redis", "Answers PING", "PASS" if rc("ping") == "PONG" else "FAIL", rc("ping"))
    pol = rc("config", "get", "maxmemory-policy").splitlines()[-1]
    rec("Redis", "Eviction policy = volatile-lru", "PASS" if pol == "volatile-lru" else "FAIL", pol)
    mem = rc("info", "memory")
    used = int(re.search(r"used_memory:(\d+)", mem).group(1)) if "used_memory:" in mem else 0
    mx = int(re.search(r"maxmemory:(\d+)", mem).group(1)) if "maxmemory:" in mem else 0
    rec("Redis", "Memory vs maxmemory", "WARN" if mx and used / mx > 0.8 else "PASS", f"{used / 2**20:.0f} MB used of {mx / 2**20:.0f} MB" if mx else f"{used / 2**20:.0f} MB used, no maxmemory set")
    ev = re.search(r"evicted_keys:(\d+)", rc("info", "stats"))
    rec("Redis", "Evictions", "WARN" if ev and int(ev.group(1)) > 0 else "PASS", f"{ev.group(1) if ev else '?'} keys evicted since start")
    rec("Redis", "XP stream (db1)", "INFO", f"{rc('-n', '1', 'xlen', 'broski:xp:log')} awards in broski:xp:log, {rc('-n', '1', 'dbsize')} keys in db1")

    out = net("""import urllib.request
def g(u):
    try: return urllib.request.urlopen(u, timeout=10).status
    except Exception as e: return type(e).__name__
print('minio', g('http://minio:9000/minio/health/live'))
print('chroma', g('http://chroma:8000/api/v2/heartbeat'), g('http://chroma:8000/api/v1/heartbeat'))
""")
    m = re.search(r"minio (\w+)", out); c = re.search(r"chroma (\w+) (\w+)", out)
    rec("MinIO", "Liveness", "PASS" if m and m.group(1) == "200" else "FAIL", m.group(1) if m else out[:80])
    rec("Chroma", "Heartbeat", "PASS" if c and "200" in c.groups() else "FAIL", " / ".join(c.groups()) if c else out[:80])


def backups():
    section("4. Backups, off-site copy, watchdog")
    code, out, _ = ps(r"""Get-ScheduledTask -TaskPath '\HyperCode\' | ForEach-Object { $i = $_ | Get-ScheduledTaskInfo; '{0}|{1}|{2}|{3}' -f $_.TaskName,$_.State,$i.LastRunTime.ToString('yyyy-MM-dd HH:mm'),$i.LastTaskResult }""")
    for l in out.splitlines():
        n, st, when, res = l.split("|")
        ok = res == "0"
        rec("Backups", f"Task '{n}'", "PASS" if ok else "FAIL", f"last run {when}, result 0x{int(res):X}, state {st}" if res.lstrip('-').isdigit() else l)
    now = time.time()
    store = Path(r"C:\HyperCodeBackups")
    for sub, pats in (("postgres", ("*.dump",)), ("stores", ("*.tar", "*.tgz", "*.tar.gz", "*.zip", "*.7z", "*.rdb", "*.tar.zst"))):
        d = store / sub
        files = sorted((f for pat in pats for f in d.rglob(pat)), key=lambda q: q.stat().st_mtime, reverse=True) if d.exists() else []
        if files:
            age_h = (now - files[0].stat().st_mtime) / 3600
            # postgres: one <dump>.sha256 per dump; stores: one SHA256SUMS per backup set folder
            sha = files[0].with_name(files[0].name + ".sha256").exists() or (files[0].parent / "SHA256SUMS").exists()
            rec("Backups", f"Newest {sub} backup in C:\\HyperCodeBackups", "PASS" if age_h < 36 else "FAIL",
                f"{files[0].name}, {age_h:.1f} h old, {files[0].stat().st_size / 2**20:.1f} MB, checksum file {'present' if sha else 'MISSING'}")
        else:
            rec("Backups", f"Newest {sub} backup in C:\\HyperCodeBackups", "FAIL", "no archive files found")
    queued = sorted(store.glob("*.7z"), key=lambda q: q.stat().st_mtime, reverse=True)
    if queued:
        age_h = (now - queued[0].stat().st_mtime) / 3600
        try:
            shutil.disk_usage("G:\\"); mounted = True
        except OSError:
            mounted = False
        rec("Backups", "Encrypted off-site archives queued locally", "WARN" if not mounted else "PASS",
            f"{len(queued)} archives, newest {age_h:.1f} h old" + ("" if mounted else ", NOT copied to Google Drive (not mounted)"))
    alog = ROOT / "backups" / "watchdog-run.log"
    if alog.exists():
        lines = alog.read_text(encoding="utf-8", errors="replace").splitlines()
        cutoff = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M")
        sent = [l for l in lines if "alert sent to Discord" in l and l[:16] >= cutoff]
        rec("Backups", "Discord alerts sent by the watchdog in the last 24 h", "WARN" if sent else "PASS", f"{len(sent)} alert(s)")
    logs = sorted((ROOT / "backups").rglob("*offsite*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if logs:
        tail = [x for x in logs[0].read_text(encoding="utf-8", errors="replace").splitlines() if x.strip()][-2:]
        rec("Backups", "Off-site log (last lines)", "INFO", " | ".join(t[:110] for t in tail))
    code, out, err = sh(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/backup_watchdog.ps1", "-DryRun"], timeout=240)
    bad = [l.strip() for l in out.splitlines() if re.search(r"ALERT|FAIL|MISSING|WARN|stale|not ok", l, re.I)]
    rec("Backups", "Watchdog dry run (all its checks)", "PASS" if code == 0 else "FAIL", f"exit {code}; " + (" || ".join(b[:120] for b in bad[:6]) or "no alert lines"))


def security(skip_auth=False):
    section("5. Security and authentication")
    if skip_auth:
        rec("Security", "Auth matrix (deliberate bad requests)", "INFO", "skipped (--skip-auth): those requests would trip the watchdog's 401/403 alert")
        return security_hygiene()
    code, out, _ = sh(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/probe_inter_agent_key.ps1"], timeout=240)
    last = [l for l in out.splitlines() if l.startswith("PROBE")]
    rejected = bool(re.search(r"=(401|403|down)", out))
    rec("Security", "Shared inter-agent key accepted by all enforcing peers", "FAIL" if rejected or code != 0 else "PASS", last[-1][:120] if last else out[-100:])
    shared, master = read("secrets/inter_agent_key.txt"), read("secrets/api_key.txt")
    old_shared = read("secrets/inter_agent_key.old.txt") if (ROOT / "secrets/inter_agent_key.old.txt").exists() else ""
    dash = read("secrets/dashboard_service_jwt.txt")
    old_dash = ""
    baks = sorted((ROOT / "secrets").glob("dashboard_service_jwt.txt.bak-jwt-rotation-*"))
    if baks:
        old_dash = baks[-1].read_text(encoding="utf-8-sig").strip()
    py = """import sys, json, urllib.request, urllib.error
def st(url, **h):
    try: return urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=12).status
    except urllib.error.HTTPError as e: return e.code
    except Exception as e: return type(e).__name__
shared, master, oldshared, dash, olddash = sys.argv[1:6]
core = 'http://hypercode-core:8000/api/v1'
out = {}
out['core agents, no credential'] = st(core + '/orchestrator/agents')
out['core agents, dashboard JWT'] = st(core + '/orchestrator/agents', Authorization='Bearer ' + dash)
out['core agents, OLD dashboard JWT'] = st(core + '/orchestrator/agents', Authorization='Bearer ' + olddash) if olddash != '-' else 'n/a'
out['core operator, master key (must be refused)'] = st(core + '/operator/morning', **{'X-API-Key': master})
out['shepherd, OLD shared key'] = st('http://safety-shepherd:8096/__authprobe', **{'X-API-Key': oldshared}) if oldshared != '-' else 'n/a'
out['shepherd, dev-master-key'] = st('http://safety-shepherd:8096/__authprobe', **{'X-API-Key': 'dev-master-key'})
out['healer, dev-master-key'] = st('http://healer-agent:8008/circuit-breaker/status', **{'X-API-Key': 'dev-master-key'})
out['healer, shared key'] = st('http://healer-agent:8008/circuit-breaker/status', **{'X-API-Key': shared})
out['healer /health (open)'] = st('http://healer-agent:8008/health')
out['bridge, shared key (must be refused)'] = st('http://broski-pets-bridge:8098/leaderboard', **{'X-API-Key': shared})
out['bridge, master key'] = st('http://broski-pets-bridge:8098/leaderboard', **{'X-API-Key': master})
out['relay, master key (must be refused)'] = st('http://evolve-relay:8097/evolve', **{'X-API-Key': master})
out['hyperhealth /checks, no key'] = st('http://hyperhealth-api:8090/checks')
out['hyperhealth /checks, master key'] = st('http://hyperhealth-api:8090/checks', **{'X-API-Key': master})
print(json.dumps(out))
"""
    res = net(py, shared, master, old_shared or "-", dash, old_dash or "-")
    try:
        d = json.loads(res.splitlines()[-1])
    except Exception:
        rec("Security", "Auth matrix", "FAIL", res[:120]); return
    want = {
        "core agents, no credential": ({401}, "core refuses an unauthenticated call"),
        "core agents, dashboard JWT": ({200}, "the re-minted dashboard JWT works"),
        "core agents, OLD dashboard JWT": ({401, 403}, "the pre-rotation dashboard JWT is dead"),
        "core operator, master key (must be refused)": ({401, 403}, "operator routes refuse the master key"),
        "shepherd, OLD shared key": ({401}, "the retired shared key is dead"),
        "shepherd, dev-master-key": ({401}, "the public default key is refused"),
        "healer, dev-master-key": ({401}, "healer refuses the public default key"),
        "healer, shared key": ({200}, "healer accepts the shared key"),
        "healer /health (open)": ({200}, "healer /health stays open"),
        "bridge, shared key (must be refused)": ({401}, "bridge refuses the shared key (it wants the master key)"),
        "bridge, master key": ({200}, "bridge accepts the master key core sends"),
        "relay, master key (must be refused)": ({401}, "evolve-relay refuses the master key (it wants the shared key)"),
        "hyperhealth /checks, no key": ({401, 422}, "hyperhealth /checks needs a key"),
        "hyperhealth /checks, master key": ({200}, "hyperhealth /checks accepts the master key"),
    }
    for k, (ok, label) in want.items():
        v = d.get(k)
        if v == "n/a":
            rec("Security", label, "INFO", "no retired copy to test with")
        else:
            rec("Security", label, "PASS" if v in ok else "FAIL", f"HTTP {v}")
    security_hygiene()


def security_hygiene():
    # secrets hygiene (names only)
    sec = ROOT / "secrets"
    dirs = [p.name for p in sec.glob("*.txt") if p.is_dir()]
    rec("Security", "Every secrets/*.txt is a FILE (not a directory Docker made)", "FAIL" if dirs else "PASS",
        ("directories: " + ", ".join(dirs) + " (a missing bind-mount source was created as an empty folder; the container sees an empty directory)") if dirs else "all files")
    files = [p for p in sec.glob("*.txt") if p.is_file()]
    empty = [p.name for p in files if p.stat().st_size == 0]
    bom = [p.name for p in files if p.read_bytes()[:3] == b"\xef\xbb\xbf"]
    rec("Security", "Secret files non-empty and BOM-free", "FAIL" if empty or bom else "PASS", ", ".join(empty + bom) or f"{len(files)} files ok")
    retired = sorted(p.name for p in sec.iterdir() if ".bak" in p.name or p.name.endswith(".old.txt"))
    rec("Security", "Retired-secret backups left on disk", "WARN" if retired else "PASS", f"{len(retired)} files: " + ", ".join(retired[:6]))
    c, o, _ = sh(["git", "check-ignore", "secrets/api_key.txt", ".env"])
    rec("Security", "secrets/ and .env are gitignored", "PASS" if o.count("\n") >= 1 else "FAIL", o.replace("\n", ", "))
    c, o, _ = sh(["git", "ls-files", "secrets", ".env"])
    rec("Security", "No secret files tracked by git", "FAIL" if [l for l in o.splitlines() if not l.endswith((".gitkeep", ".example", "README.md"))] else "PASS", o[:100] or "none tracked")
    code, ids, _ = docker(["ps", "-q"], timeout=30)
    names = []
    for cid in ids.split():
        c, env, _ = docker(["inspect", "--format", "{{.Name}} {{range .Config.Env}}{{println .}}{{end}}", cid], timeout=30)
        if re.search(r"^[A-Z_]*API_KEY=dev-master-key$", env, re.M):
            names.append(env.split()[0].lstrip("/"))
    rec("Security", "Containers still carrying the public default key in env", "WARN" if names else "PASS", f"{len(names)}: " + ", ".join(names[:12]) + ("  (ignored where a *_FILE secret wins)" if names else ""))
    master = read("secrets/api_key.txt")
    out = net("""import urllib.request, json, re, sys
rows = json.loads(urllib.request.urlopen(urllib.request.Request('http://hyperhealth-api:8090/checks?enabled_only=false', headers={'X-API-Key': sys.argv[1]}), timeout=15).read())
print([r['name'] for r in rows if re.search(r'://[^/@\\s]+:[^/@\\s]+@', r.get('target',''))])
""", master)
    rec("Security", "No password stored in hyperhealth check targets", "FAIL" if "postgres" in out else "PASS", f"targets embedding a password: {out[:100]}")


def signal_writer():
    sig = ROOT / "ram-signal" / "ram.json"
    if sig.exists():
        age = (time.time() - sig.stat().st_mtime) / 60
        rec("Throttle", "RAM-guard signal file is fresh (written by the scheduled task)", "FAIL" if age > 10 else "PASS",
            f"last written {age:.0f} min ago" if age < 120 else f"last written {age / 60:.1f} h ago: the writer is not running, so throttle-agent reads UNKNOWN")
    else:
        rec("Throttle", "RAM-guard signal file", "FAIL", "ram-signal/ram.json missing")
    code, out, _ = ps("(Get-Process pythonw -ErrorAction SilentlyContinue | Measure-Object).Count")
    rec("Throttle", "Signal writer process (pythonw ram_guard.py) running", "PASS" if out.strip() not in ("", "0") else "FAIL", f"{out.strip() or 0} pythonw process(es)")


def apps():
    section("6. Applications")
    signal_writer()
    base = "http://127.0.0.1:8088"
    for p in ("/", "/agents", "/control", "/docker-zone", "/flows", "/grafana", "/health", "/ide", "/mcp", "/mission", "/sensory"):
        t = time.time()
        try:
            s = urllib.request.urlopen(base + p, timeout=40).status
        except urllib.error.HTTPError as e:
            s = e.code
        except Exception as e:
            s = type(e).__name__
        ms = (time.time() - t) * 1000
        rec("Dashboard", f"page {p}", "PASS" if s == 200 and ms < 3000 else "WARN" if s == 200 else "FAIL", f"HTTP {s}, {ms:.0f} ms")
    for a in ("agents", "broski", "fleet", "health", "logs", "metrics", "orchestrator", "pulse", "safety", "tasks", "ws-token", "crew/morning", "crew/panic"):
        t = time.time()
        try:
            r = urllib.request.urlopen(f"{base}/api/{a}", timeout=40); s = r.status; body = r.read()
            try:
                json.loads(body); note = "valid JSON"
            except Exception:
                note = "not JSON"
        except urllib.error.HTTPError as e:
            s, note = e.code, ""
        except Exception as e:
            s, note = type(e).__name__, ""
        rec("Dashboard", f"API /api/{a}", "PASS" if s == 200 else "FAIL", f"HTTP {s}, {(time.time() - t) * 1000:.0f} ms, {note}")
    def j(p):
        try:
            return json.load(urllib.request.urlopen(f"{base}/api/{p}", timeout=40))
        except Exception:
            return {}
    pulse = j("pulse")
    rec("Dashboard", "Pulse not degraded", "FAIL" if pulse.get("degraded") else "PASS", f"degraded={pulse.get('degraded')}, agents {pulse.get('healthy_agents')}/{pulse.get('total_agents')}, XP {pulse.get('total_xp')}, coins {pulse.get('broski_coins')}")
    fl = j("fleet").get("summary", {})
    rec("Fleet", "Agent fleet", "INFO", f"{fl.get('healthy')} healthy, {fl.get('running')} running, {fl.get('down')} down, {fl.get('not_deployed')} not deployed, {fl.get('total')} total, crash-looping {fl.get('crash_looping')}")
    rec("Fleet", "No crash-looping agents", "FAIL" if fl.get("crash_looping") else "PASS", f"{fl.get('crash_looping')} crash-looping")
    m = j("metrics")
    rec("Fleet", "Error rate / DLQ / alerts", "WARN" if (m.get("errorRatePct") or 0) > 5 or m.get("dlqDepth") or m.get("alertFiring") else "PASS", f"error {m.get('errorRatePct')}%, DLQ {m.get('dlqDepth')}, firing {m.get('alertFiring')}, avg {m.get('avgResponseMs')} ms")
    ev = j("safety").get("events", [])
    blocks = [e for e in ev if e.get("decision") not in ("ALLOW", None)]
    rec("Safety", "Safety Shepherd decisions", "WARN" if blocks else "PASS", f"{len(ev)} recent, {len(blocks)} not ALLOW")
    out = net("""import urllib.request, json, sys
r = urllib.request.Request('http://throttle-agent:8080/signal', headers={'X-API-Key': sys.argv[1]})
try:
    d = json.loads(urllib.request.urlopen(r, timeout=10).read()); print(json.dumps({k: d.get(k) for k in ('mode','verdict','signal','state','would_act','age_s','status') if k in d}))
except Exception as e: print('ERR', type(e).__name__)
""", read("secrets/inter_agent_key.txt"))
    rec("Throttle", "Throttle-agent signal + mode", "WARN" if "UNKNOWN" in out.upper() or out.startswith("ERR") else "PASS", out[:160])
    for c in ("agent-registry", "crew-orchestrator", "safety-shepherd", "governor", "healer-agent", "broski-economy-consumer"):
        code, o, _ = docker(["inspect", "--format", "{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}", c], timeout=30)
        rec("Services", f"{c}", "PASS" if "running" in o and "unhealthy" not in o else "FAIL", o or "not found")
    c, o, _ = docker(["logs", "--tail", "400", "broski-economy-consumer"], timeout=40)
    errs = len(re.findall(r"FAILED|ERROR|Traceback", o))
    rec("Economy", "Economy consumer log (last 400 lines)", "WARN" if errs else "PASS", f"{errs} error lines")


def repo(skip_tests):
    section("7. Repository, CI and unit tests")
    wf = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
    stray = [w.name for w in wf if len(re.findall(r"^on:", w.read_text(encoding="utf-8"), re.M)) > 1]
    rec("CI", "Workflow files with a duplicate top-level 'on:' key", "FAIL" if stray else "PASS",
        f"{len(stray)} of {len(wf)} files (GitHub rejects these before running any job): " + ", ".join(stray[:24]) if stray else f"0 of {len(wf)}")
    c, o, _ = sh(["git", "status", "--porcelain"])
    rec("Repo", "Working tree clean", "WARN" if o else "PASS", f"{len(o.splitlines())} changed/untracked files" if o else "clean")
    c, o, _ = sh(["git", "rev-parse", "--abbrev-ref", "HEAD"]); rec("Repo", "On branch", "PASS" if o == "main" else "WARN", o)
    c, o, _ = sh(["git", "fetch", "-q"], timeout=60)
    c, o, _ = sh(["git", "rev-list", "--left-right", "--count", "main...origin/main"]); rec("Repo", "main vs origin/main (ahead/behind)", "PASS" if o.split() == ["0", "0"] else "WARN", o.replace("\t", " / "))
    c, o, _ = sh(["gh", "run", "list", "--branch", "main", "--limit", "12", "--json", "name,conclusion,createdAt"], timeout=60)
    try:
        runs = json.loads(o)
        bad = [r["name"] for r in runs if r["conclusion"] == "failure"]
        rec("CI", "Latest runs on main", "FAIL" if bad else "PASS", f"{len(runs)} newest runs, {len(bad)} failed" + (": " + ", ".join(b.split("/")[-1] for b in bad[:8]) if bad else ""))
    except Exception:
        rec("CI", "Latest runs on main", "WARN", "gh unavailable")
    c, o, _ = sh(["gh", "pr", "list", "--state", "open", "--json", "number,title"], timeout=60)
    try:
        prs = json.loads(o); deps = [p for p in prs if p["title"].startswith("chore(deps)")]
        rec("CI", "Open pull requests", "WARN" if len(deps) > 10 else "INFO", f"{len(prs)} open, {len(deps)} of them dependency bumps (oldest #{min((p['number'] for p in prs), default='-')})")
    except Exception:
        pass
    if skip_tests:
        rec("Tests", "Unit tests", "INFO", "skipped (--skip-tests)"); return
    code, out, err = sh([sys.executable, "-m", "pytest", ".github/scripts/tests", "scripts/test_rotate_jwt_secret.py", "scripts/test_mint_agent_keys.py", "-q", "-p", "no:cacheprovider"], timeout=600)
    tail = [l for l in out.splitlines() if re.search(r"passed|failed|error", l)][-1:] or [err[-100:]]
    rec("Tests", "pytest: secret-env sync, XP reconcile, key rotation/minting, pets-bridge guard", "PASS" if code == 0 else "FAIL", tail[0])
    code, out, err = sh([sys.executable, "-m", "unittest", "discover", "-s", "scripts", "-p", "test_broski_economy_consumer.py"], timeout=300)
    tail = (out + "\n" + err).strip().splitlines()[-1:] or [""]
    rec("Tests", "unittest: economy consumer", "PASS" if code == 0 else "FAIL", tail[0])
    code, out, err = sh([sys.executable, "scripts/vendor_secret_env.py", "--check"], timeout=60)
    rec("Tests", "vendored read_secret copies identical", "PASS" if code == 0 else "FAIL", f"{out.count('ok ')} files ok" + (f", drift: {out[-80:]}" if code else ""))


def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--json"); ap.add_argument("--skip-tests", action="store_true"); ap.add_argument("--skip-auth", action="store_true", help="skip the deliberate bad-credential requests (they trip the watchdog)")
    a = ap.parse_args()
    t0 = time.time()
    print(f"HyperCode full system test, {datetime.now():%Y-%m-%d %H:%M} (read-only)")
    for f in (host, containers, datastores, backups, (lambda: security(a.skip_auth)), apps):
        try:
            f()
        except Exception as e:  # a broken check must not hide the rest
            rec(getattr(f, "__name__", "check"), "check crashed", "FAIL", f"{type(e).__name__}: {str(e)[:120]}")
    try:
        repo(a.skip_tests)
    except Exception as e:
        rec("repo", "check crashed", "FAIL", f"{type(e).__name__}: {str(e)[:120]}")
    n = {s: sum(1 for r in R if r["status"] == s) for s in ("PASS", "WARN", "FAIL", "INFO")}
    print(f"\nSUMMARY: {n['PASS']} pass, {n['WARN']} warn, {n['FAIL']} fail, {n['INFO']} info  ({time.time() - t0:.0f}s)")
    if a.json:
        Path(a.json).write_text(json.dumps({"when": datetime.now().isoformat(timespec="seconds"), "counts": n, "results": R}, indent=1), encoding="utf-8")
    return 1 if n["FAIL"] else 0


if __name__ == "__main__":
    sys.exit(main())
