#!/usr/bin/env python3
"""RAM pre-flight guard for the 8 GB Windows + WSL2 + Docker box. Read-only: it only MEASURES.

Why it exists: on 2026-10-03 the Windows HOST ran out of RAM (1 MB free, "Memory Compression" 4.5 GB) while WSL still
reported 1.3 GB available, so Docker hung and every container read "unhealthy". `wsl -e free -m` alone cannot see that.
This checks the host, the WSL VM and Docker together, says GREEN / AMBER / RED, and exits non-zero when it is not safe.

    python scripts/ram_guard.py                      # report only (exit 0 unless RED)
    python scripts/ram_guard.py --for build          # strict: a build needs GREEN (exit 1 on AMBER, 2 on RED)
    python scripts/ram_guard.py --for restart        # only RED blocks
    python scripts/ram_guard.py --for build --wait 120   # poll every 10 s until OK or the time is up
    python scripts/ram_guard.py --json --out ram.json    # machine-readable (for a future throttle-agent signal)

Exit codes: 0 = OK for the requested purpose, 1 = AMBER and the purpose needs GREEN, 2 = RED (or Docker unresponsive).

The default thresholds were calibrated on ONE machine on ONE day (2026-10-03):
  thrash (RED):   host free 1 MB, compression 4,511 MB, WSL avail ~1,200-1,317 MB, swap 1,085 MB
  fine (GREEN):   host free 767-823 MB, compression 1,546-1,935 MB, WSL avail 1,450-1,780 MB
Swap used was ~1.08 GB in BOTH states, so it is informational only (high thresholds). Tune with flags.
ASCII output only (the Windows console is cp1252). Never prints secrets: it reads memory numbers and container NAMES.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from typing import Any, Optional

GREEN, AMBER, RED = "GREEN", "AMBER", "RED"
_RANK = {GREEN: 0, AMBER: 1, RED: 2}

DEFAULTS: dict[str, int] = {
    "wsl_avail_red": 1200,       # MB, the project's existing stop rule
    "wsl_avail_amber": 1500,     # MB, the project's existing "before ANY build" floor
    "host_free_red": 100,        # MB
    "host_free_amber": 300,      # MB
    "compression_red": 3500,     # MB, Windows "Memory Compression" working set
    "compression_amber": 2500,   # MB
    "swap_red": 1900,            # MB used (of 2048) - informational
    "swap_amber": 1500,          # MB used
}

# Containers the throttle design treats as optional (safe to stop for a build). Names only; never stopped by this script.
OPTIONAL_STACKS = (
    "observability: grafana loki tempo pyroscope promtail node-exporter cadvisor alertmanager celery-exporter prometheus prometheus-cloud grafana-agent",
    "crew proxy (if on): fcc-proxy",
)


@dataclass
class Metrics:
    host_free_mb: Optional[int] = None
    host_total_mb: Optional[int] = None
    compression_mb: Optional[int] = None
    wsl_avail_mb: Optional[int] = None
    wsl_total_mb: Optional[int] = None
    swap_used_mb: Optional[int] = None
    swap_total_mb: Optional[int] = None
    docker_ok: Optional[bool] = None
    unhealthy: Optional[list[str]] = None
    top_host_procs: Optional[list[str]] = None


@dataclass
class Finding:
    name: str
    level: str
    value: str
    detail: str


# ── pure logic (unit-tested) ────────────────────────────────────────────────
def _low_is_bad(v: Optional[int], red: int, amber: int) -> str:
    if v is None:
        return AMBER
    return RED if v < red else AMBER if v < amber else GREEN


def _high_is_bad(v: Optional[int], red: int, amber: int) -> str:
    if v is None:
        return AMBER
    return RED if v > red else AMBER if v > amber else GREEN


def evaluate(m: Metrics, th: Optional[dict[str, int]] = None, check_docker: bool = True) -> tuple[str, list[Finding]]:
    """(overall level, findings). An unreadable number is AMBER, never silently GREEN.

    check_docker=False (--skip-docker) leaves the docker finding out entirely: skipping it on purpose is not a warning.
    """
    t = {**DEFAULTS, **(th or {})}
    f: list[Finding] = []

    lv = _low_is_bad(m.host_free_mb, t["host_free_red"], t["host_free_amber"])
    f.append(Finding("host free", lv, "unreadable" if m.host_free_mb is None else f"{m.host_free_mb} MB",
                     f"RED<{t['host_free_red']} AMBER<{t['host_free_amber']} (Windows free physical RAM)"))

    lv = _high_is_bad(m.compression_mb, t["compression_red"], t["compression_amber"])
    f.append(Finding("host compression", lv, "unreadable" if m.compression_mb is None else f"{m.compression_mb} MB",
                     f"RED>{t['compression_red']} AMBER>{t['compression_amber']} (Windows 'Memory Compression'; high = the host is squeezing)"))

    lv = _low_is_bad(m.wsl_avail_mb, t["wsl_avail_red"], t["wsl_avail_amber"])
    f.append(Finding("WSL available", lv, "unreadable" if m.wsl_avail_mb is None else f"{m.wsl_avail_mb} MB",
                     f"RED<{t['wsl_avail_red']} AMBER<{t['wsl_avail_amber']} (the project's stop rule / build floor)"))

    lv = _high_is_bad(m.swap_used_mb, t["swap_red"], t["swap_amber"])
    f.append(Finding("WSL swap used", lv, "unreadable" if m.swap_used_mb is None else f"{m.swap_used_mb} MB",
                     f"RED>{t['swap_red']} AMBER>{t['swap_amber']} (informational: ~1.1 GB in both good and bad states)"))

    if not check_docker:
        pass
    elif m.docker_ok is False:
        f.append(Finding("docker", RED, "unresponsive", "`docker version` did not answer in time (the engine is stalling)"))
    elif m.docker_ok is None:
        f.append(Finding("docker", AMBER, "not checked", "docker CLI missing or skipped"))
    else:
        n = len(m.unhealthy or [])
        f.append(Finding("docker", AMBER if n else GREEN, "responsive, " + (f"{n} unhealthy" if n else "0 unhealthy"),
                         ("unhealthy: " + ", ".join((m.unhealthy or [])[:8])) if n else "engine answers, no unhealthy containers"))

    overall = max((x.level for x in f), key=lambda lv_: _RANK[lv_])
    return overall, f


def exit_code(purpose: str, overall: str) -> int:
    """0 = OK for this purpose. A build needs GREEN; anything else is blocked only by RED."""
    if overall == RED:
        return 2
    if overall == AMBER and purpose == "build":
        return 1
    return 0


def parse_free_m(text: str) -> dict[str, Optional[int]]:
    """Parse `free -m` into total/avail/swap numbers (None if a line is missing)."""
    out: dict[str, Optional[int]] = {"total": None, "avail": None, "swap_used": None, "swap_total": None}
    for line in (text or "").splitlines():
        parts = line.split()
        if not parts:
            continue
        if parts[0].lower().startswith("mem") and len(parts) >= 7 and all(p.lstrip("-").isdigit() for p in parts[1:7]):
            out["total"], out["avail"] = int(parts[1]), int(parts[6])
        elif parts[0].lower().startswith("swap") and len(parts) >= 3 and all(p.isdigit() for p in parts[1:3]):
            out["swap_total"], out["swap_used"] = int(parts[1]), int(parts[2])
    return out


def parse_host_json(text: str) -> dict[str, Any]:
    try:
        d = json.loads((text or "").strip().splitlines()[-1])
        return d if isinstance(d, dict) else {}
    except (ValueError, IndexError):
        return {}


# ── measurement (touches the machine; read-only) ────────────────────────────
def _run(cmd: list[str], timeout: float) -> Optional[str]:
    """stdout, or None on timeout / missing binary / non-zero exit."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return None
    return r.stdout if r.returncode == 0 else None


_PS = (
    "$o=Get-CimInstance Win32_OperatingSystem;"
    "$c=(Get-Process 'Memory Compression' -ErrorAction SilentlyContinue).WorkingSet64;"
    "$t=Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 5 | "
    "ForEach-Object { '{0} {1}MB' -f $_.ProcessName,[int]($_.WorkingSet64/1MB) };"
    "@{free=[int]($o.FreePhysicalMemory/1024);total=[int]($o.TotalVisibleMemorySize/1024);"
    "compression=[int]($c/1MB);top=@($t)} | ConvertTo-Json -Compress"
)


def measure(skip_docker: bool = False) -> Metrics:
    m = Metrics()
    if os.name == "nt":
        d = parse_host_json(_run(["powershell", "-NoProfile", "-NonInteractive", "-Command", _PS], 30) or "")
        m.host_free_mb, m.host_total_mb, m.compression_mb = d.get("free"), d.get("total"), d.get("compression")
        top = d.get("top")
        m.top_host_procs = [str(x) for x in top] if isinstance(top, list) else None
        free_txt = _run(["wsl", "-e", "free", "-m"], 25)
    else:  # running inside Linux/WSL: no Windows host view
        free_txt = _run(["free", "-m"], 10)
    w = parse_free_m(free_txt or "")
    m.wsl_total_mb, m.wsl_avail_mb, m.swap_used_mb, m.swap_total_mb = w["total"], w["avail"], w["swap_used"], w["swap_total"]
    if not skip_docker:
        ver = _run(["docker", "version", "--format", "{{.Server.Version}}"], 10)
        m.docker_ok = bool(ver and ver.strip())
        if m.docker_ok:
            ps = _run(["docker", "ps", "--filter", "health=unhealthy", "--format", "{{.Names}}"], 20)
            m.unhealthy = [n for n in (ps or "").split() if n]
    return m


# ── reporting ───────────────────────────────────────────────────────────────
def advice(overall: str, m: Metrics) -> list[str]:
    if overall == GREEN:
        return []
    tips = [
        "Close heavy Windows apps first (browsers, IDEs): the HOST is the part no container can free.",
        "Optional containers you can stop BY NAME (never `compose down`): " + "; ".join(OPTIONAL_STACKS),
        "Do not start anything new or build until this is GREEN. Wait, then re-run (add --wait 120).",
    ]
    if m.top_host_procs:
        tips.insert(1, "Biggest Windows processes now: " + ", ".join(m.top_host_procs))
    return tips


def render(purpose: str, overall: str, findings: list[Finding], m: Metrics, code: int) -> str:
    lines = [f"RAM guard - for: {purpose} - {time.strftime('%H:%M:%S')}"]
    for x in findings:
        lines.append(f"  {x.name:<17} {x.value:<28} {x.level:<6} {x.detail}")
    verdict = {0: "OK" if overall == GREEN else "OK (with warnings)", 1: "NOT OK - a build needs GREEN", 2: "NOT OK - RED, stop"}[code]
    lines.append(f"VERDICT: {overall} - {verdict}")
    lines += ["  * " + t for t in advice(overall, m)]
    return "\n".join(lines)


def to_json(purpose: str, overall: str, findings: list[Finding], m: Metrics, code: int) -> dict[str, Any]:
    return {"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "for": purpose, "overall": overall, "exit_code": code,
            "metrics": asdict(m), "findings": [asdict(x) for x in findings]}


def write_atomic(path: str, data: dict[str, Any]) -> None:
    """Write-then-replace in the same directory, so a reader never sees a half-written file."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    os.replace(tmp, path)


def run_loop(a: argparse.Namespace, th: dict[str, int]) -> int:
    """The host-side signal writer: measure every a.loop seconds, rewrite a.out, print one ASCII line per cycle."""
    d = os.path.dirname(os.path.abspath(a.out))
    os.makedirs(d, exist_ok=True)
    print(f"ram_guard loop: every {a.loop}s -> {a.out} (Ctrl+C to stop)", flush=True)
    try:
        while True:
            m = measure(a.skip_docker)
            overall, findings = evaluate(m, th, check_docker=not a.skip_docker)
            write_atomic(a.out, to_json(a.purpose, overall, findings, m, exit_code(a.purpose, overall)))
            print(f"{time.strftime('%H:%M:%S')} {overall:<5} host_free={m.host_free_mb} compression={m.compression_mb} "
                  f"wsl_avail={m.wsl_avail_mb}", flush=True)
            time.sleep(max(5, a.loop))
    except KeyboardInterrupt:
        print("stopped", flush=True)
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Read-only RAM pre-flight guard (host + WSL + Docker).")
    p.add_argument("--for", dest="purpose", default="check", choices=["check", "build", "restart", "start"],
                   help="build = needs GREEN; the others are blocked only by RED")
    p.add_argument("--wait", type=int, default=0, metavar="SECONDS", help="re-check every 10 s until OK or the time is up")
    p.add_argument("--json", action="store_true", help="print JSON instead of the table")
    p.add_argument("--out", metavar="FILE", help="also write the JSON here (atomic)")
    p.add_argument("--skip-docker", action="store_true", help="do not call docker (and do not judge it)")
    p.add_argument("--loop", type=int, default=0, metavar="SECONDS",
                   help="keep running: measure every SECONDS and rewrite --out (the host-side signal writer for throttle-agent). "
                        "Needs --out. Stop with Ctrl+C.")
    for k, v in DEFAULTS.items():
        p.add_argument("--" + k.replace("_", "-"), type=int, default=v, help=f"threshold (default {v})")
    a = p.parse_args(argv)
    th = {k: getattr(a, k) for k in DEFAULTS}

    if a.loop:
        if not a.out:
            p.error("--loop needs --out FILE (it is the signal writer)")
        return run_loop(a, th)

    deadline = time.time() + max(0, a.wait)
    while True:
        m = measure(a.skip_docker)
        overall, findings = evaluate(m, th, check_docker=not a.skip_docker)
        code = exit_code(a.purpose, overall)
        if code == 0 or time.time() >= deadline:
            break
        time.sleep(10)

    data = to_json(a.purpose, overall, findings, m, code)
    if a.out:
        write_atomic(a.out, data)
    print(json.dumps(data) if a.json else render(a.purpose, overall, findings, m, code))
    return code


if __name__ == "__main__":
    sys.exit(main())
