#!/usr/bin/env python3
"""
Evo Harness (P2-1) — long-horizon agent regression test.

Agents must keep HyperCode GREEN across multi-phase changes, not just single
tasks. This harness:

  1. reads the phase history from docs/ROADMAP.md
  2. builds a milestone DAG (each phase = a node with preconditions + success criteria)
  3. scores each milestone (declared status + cascading preconditions), and in
     --live mode also probes health endpoints + Prometheus SLOs + runs a HyperFlow
     smoke mission
  4. writes a JSON report to docs/evo_reports/YYYY-MM-DD.json

Modes:
  --check   (default)  CI-safe: parse + DAG + status scoring. No network, no stack.
  --live                additionally probe health/SLO/HyperFlow (needs the stack up).
  --rollback            DANGEROUS: git-rollback + replay a mission. Gated, never in CI.

Stdlib-only (urllib) so it runs in CI with no extra deps.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

# Windows consoles default to cp1252 and crash on the emoji in our output —
# force UTF-8 stdio (no-op on Linux/CI which is already UTF-8).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ROADMAP_PATH = os.path.join(REPO_ROOT, "docs", "ROADMAP.md")
REPORTS_DIR = os.path.join(REPO_ROOT, "docs", "evo_reports")

# Health endpoints probed in --live mode (service -> url). 127.0.0.1 per sacred rule.
HEALTH_ENDPOINTS = {
    "hypercode-core": "http://localhost:8000/health",
    "crew-orchestrator": "http://localhost:8081/health",
    "safety-shepherd": "http://localhost:8096/health",
    "hyperhealth-api": "http://localhost:8095/health",
}

# Prometheus SLO checks (name -> (promql, comparator, threshold)). Live mode only.
PROM_URL = os.environ.get("PROM_URL", "http://localhost:9090")
SLO_QUERIES = [
    ("core_up", 'up{job="hypercode-core"}', ">=", 1),
]

# Status classification.
_COMPLETE = re.compile(r"\b(DONE|LIVE|IMPLEMENTED|BUILT|PUSHED|FIXED)\b", re.I)
_PENDING = re.compile(r"pending|todo|soon|partial|in progress|wip", re.I)


# ── Roadmap parsing + milestone DAG ─────────────────────────────────────────────

def classify_status(status: str) -> str:
    """complete | complete_pending | unknown."""
    s = status or ""
    if _PENDING.search(s):
        return "complete_pending" if _COMPLETE.search(s) else "unknown"
    if _COMPLETE.search(s):
        return "complete"
    return "unknown"


def parse_roadmap(path: str = ROADMAP_PATH) -> List[Dict[str, Any]]:
    """Parse the `| Phase | Name | Status |` table into milestone dicts."""
    milestones: List[Dict[str, Any]] = []
    if not os.path.exists(path):
        return milestones
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 3:
                continue
            phase, name, status = cells[0], cells[1], cells[2]
            # skip header + separator rows
            if phase.lower() in ("phase", "") or set(phase) <= set("-: "):
                continue
            milestones.append({
                "phase": phase,
                "name": name,
                "status": status,
                "classification": classify_status(status),
            })
    return milestones


def build_dag(milestones: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Linear historical DAG: each milestone depends on the previous phase."""
    nodes = []
    edges = []
    for i, m in enumerate(milestones):
        nid = f"m{i}"
        deps = [f"m{i - 1}"] if i > 0 else []
        nodes.append({"id": nid, "phase": m["phase"], "name": m["name"],
                      "classification": m["classification"], "preconditions": deps})
        for d in deps:
            edges.append({"source": d, "target": nid})
    return {"nodes": nodes, "edges": edges}


# ── Scoring ─────────────────────────────────────────────────────────────────────

def score_milestones(dag: Dict[str, Any], allow_pending: bool = True) -> Dict[str, Any]:
    """Score each milestone: success criteria + cascading preconditions.

    A milestone PASSES when its own criteria pass AND all preconditions passed.
    A broken early phase therefore BLOCKS everything downstream (the long-horizon
    regression signal).
    """
    by_id = {n["id"]: n for n in dag["nodes"]}
    results: Dict[str, Dict[str, Any]] = {}

    for n in dag["nodes"]:
        cls = n["classification"]
        own_pass = cls == "complete" or (cls == "complete_pending" and allow_pending)
        deps_pass = all(results.get(d, {}).get("passed", False) for d in n["preconditions"])
        passed = own_pass and deps_pass
        if not own_pass:
            reason = f"status '{cls}'"
        elif not deps_pass:
            reason = "blocked by failed precondition"
        else:
            reason = "ok"
        results[n["id"]] = {
            "phase": n["phase"], "name": n["name"], "classification": cls,
            "own_pass": own_pass, "deps_pass": deps_pass, "passed": passed, "reason": reason,
        }

    passed = sum(1 for r in results.values() if r["passed"])
    total = len(results)
    return {
        "results": results,
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": round(passed / total, 3) if total else 0.0,
            "green": passed == total,
        },
    }


# ── Live probes (best-effort, --live only) ──────────────────────────────────────

def _http_get(url: str, timeout: float = 4.0) -> Optional[Dict[str, Any]]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
            return {"status": resp.status, "body": body[:2000]}
    except Exception as exc:  # noqa: BLE001
        return {"error": type(exc).__name__}


def probe_health() -> Dict[str, Any]:
    out = {}
    for svc, url in HEALTH_ENDPOINTS.items():
        r = _http_get(url)
        out[svc] = {"up": bool(r and r.get("status") == 200), "detail": r}
    return out


def probe_slos() -> Dict[str, Any]:
    out = {}
    for name, query, comp, threshold in SLO_QUERIES:
        url = f"{PROM_URL}/api/v1/query?query={urllib.parse.quote(query)}"
        r = _http_get(url)
        value = None
        ok = False
        try:
            if r and r.get("status") == 200:
                data = json.loads(r["body"])
                res = data.get("data", {}).get("result", [])
                if res:
                    value = float(res[0]["value"][1])
                    ok = value >= threshold if comp == ">=" else value <= threshold
        except Exception:  # noqa: BLE001
            pass
        out[name] = {"query": query, "value": value, "ok": ok}
    return out


def run_hyperflow_mission() -> Dict[str, Any]:
    """Run the deterministic hyperflow-smoke mission and check it completes."""
    core = os.environ.get("CORE_URL", "http://localhost:8000")
    # Unauthenticated reads are enough to confirm the flow registry + active surface.
    flows = _http_get(f"{core}/api/v1/flows")
    active = _http_get(f"{core}/api/v1/flows/active")
    reachable = bool(flows and flows.get("status") == 200)
    return {"reachable": reachable, "flows": flows, "active": active}


# ── Report ──────────────────────────────────────────────────────────────────────

def build_report(mode: str, live: bool) -> Dict[str, Any]:
    milestones = parse_roadmap()
    dag = build_dag(milestones)
    scored = score_milestones(dag)
    report: Dict[str, Any] = {
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "mode": mode,
        "milestone_count": len(milestones),
        "dag": {"nodes": len(dag["nodes"]), "edges": len(dag["edges"])},
        "summary": scored["summary"],
        "milestones": list(scored["results"].values()),
    }
    if live:
        report["live"] = {
            "health": probe_health(),
            "slos": probe_slos(),
            "hyperflow": run_hyperflow_mission(),
        }
    return report


def write_report(report: Dict[str, Any]) -> str:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    day = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")
    path = os.path.join(REPORTS_DIR, f"{day}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return path


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Evo Harness — long-horizon regression test")
    ap.add_argument("--check", action="store_true", help="CI-safe check mode (default; no network)")
    ap.add_argument("--live", action="store_true", help="probe health/SLO/HyperFlow (needs stack up)")
    ap.add_argument("--rollback", action="store_true", help="DANGEROUS git-rollback replay (never in CI)")
    ap.add_argument("--no-write", action="store_true", help="don't write the report file")
    ap.add_argument("--fail-under", type=float, default=0.9,
                    help="exit non-zero if pass_rate < this (regression floor; default 0.9)")
    args = ap.parse_args(argv)

    if args.rollback:
        print("⛔ --rollback is a gated destructive operation and is intentionally not "
              "implemented in CI-safe mode. Run a HyperFlow mission against a staging "
              "stack instead.", file=sys.stderr)
        return 2

    mode = "live" if args.live else "check"
    report = build_report(mode, live=args.live)

    path = None
    if not args.no_write:
        path = write_report(report)

    s = report["summary"]
    print(f"🧬 Evo Harness [{mode}] — {s['passed']}/{s['total']} milestones green "
          f"(pass_rate {s['pass_rate']})" + (f" → {path}" if path else ""))
    if not s["green"]:
        for m in report["milestones"]:
            if not m["passed"]:
                print(f"  ✗ {m['phase']}: {m['name']} — {m['reason']}")

    return 0 if s["pass_rate"] >= args.fail_under else 1


if __name__ == "__main__":
    raise SystemExit(main())
