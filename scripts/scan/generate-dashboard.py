#!/usr/bin/env python3
"""
HyperCode V2.4 — Scan Report Dashboard Generator
Aggregates all JSON scan reports into a single HTML executive dashboard.

Usage:
    python3 scripts/scan/generate-dashboard.py \
        --reports-dir reports/all \
        --output reports/dashboard.html \
        --commit abc1234 \
        --branch main \
        --run-id 12345
"""

import argparse
import glob
import json
import os
import sys
from datetime import datetime
from pathlib import Path


# ── Report parsers ────────────────────────────────────────────────────────

def parse_bandit(path: str) -> dict:
    try:
        with open(path) as f:
            data = json.load(f)
        results = data.get("results", [])
        metrics = data.get("metrics", {}).get("_totals", {})
        high = sum(1 for r in results if r.get("issue_severity") == "HIGH")
        medium = sum(1 for r in results if r.get("issue_severity") == "MEDIUM")
        low = sum(1 for r in results if r.get("issue_severity") == "LOW")
        return {
            "tool": "Bandit", "category": "SAST",
            "status": "FAIL" if high > 0 else "PASS",
            "summary": f"HIGH: {high}, MEDIUM: {medium}, LOW: {low}",
            "total": len(results),
            "findings": [
                {
                    "severity": r.get("issue_severity", "?"),
                    "file": r.get("filename", "?"),
                    "line": r.get("line_number", "?"),
                    "message": r.get("issue_text", "?"),
                    "test": r.get("test_name", "?"),
                }
                for r in results if r.get("issue_severity") in ("HIGH", "MEDIUM")
            ][:20],
        }
    except Exception as e:
        return {"tool": "Bandit", "category": "SAST", "status": "ERROR", "summary": str(e), "total": 0, "findings": []}


def parse_semgrep(path: str) -> dict:
    try:
        with open(path) as f:
            data = json.load(f)
        results = data.get("results", [])
        errors = data.get("errors", [])
        high = sum(1 for r in results if r.get("extra", {}).get("severity", "").upper() == "ERROR")
        return {
            "tool": "Semgrep", "category": "SAST",
            "status": "FAIL" if high > 0 else "PASS",
            "summary": f"Errors: {high}, Total findings: {len(results)}",
            "total": len(results),
            "findings": [
                {
                    "severity": r.get("extra", {}).get("severity", "?"),
                    "file": r.get("path", "?"),
                    "line": r.get("start", {}).get("line", "?"),
                    "message": r.get("extra", {}).get("message", "?"),
                    "test": r.get("check_id", "?"),
                }
                for r in results if r.get("extra", {}).get("severity", "").upper() == "ERROR"
            ][:20],
        }
    except Exception as e:
        return {"tool": "Semgrep", "category": "SAST", "status": "ERROR", "summary": str(e), "total": 0, "findings": []}


def parse_gitleaks(path: str) -> dict:
    try:
        with open(path) as f:
            findings = json.load(f)
        if findings is None:
            findings = []
        return {
            "tool": "Gitleaks", "category": "Secrets",
            "status": "FAIL" if findings else "PASS",
            "summary": f"{len(findings)} secret(s) found",
            "total": len(findings),
            "findings": [
                {
                    "severity": "HIGH",
                    "file": s.get("File", "?"),
                    "line": s.get("StartLine", "?"),
                    "message": f"Rule: {s.get('RuleID','?')} — {s.get('Description','')[:60]}",
                    "test": s.get("RuleID", "?"),
                }
                for s in (findings or [])
            ][:20],
        }
    except Exception as e:
        return {"tool": "Gitleaks", "category": "Secrets", "status": "ERROR", "summary": str(e), "total": 0, "findings": []}


def parse_pip_audit(path: str) -> dict:
    try:
        with open(path) as f:
            data = json.load(f)
        vulns = []
        if isinstance(data, list):
            for pkg in data:
                for v in pkg.get("vulns", []):
                    vulns.append({"package": pkg["name"], "version": pkg["version"], **v})
        return {
            "tool": "pip-audit", "category": "Dependencies",
            "status": "FAIL" if vulns else "PASS",
            "summary": f"{len(vulns)} Python CVE(s) found",
            "total": len(vulns),
            "findings": [
                {
                    "severity": "HIGH",
                    "file": f"{v.get('package','?')}=={v.get('version','?')}",
                    "line": "-",
                    "message": v.get("description", "")[:80],
                    "test": v.get("id", "?"),
                }
                for v in vulns
            ][:20],
        }
    except Exception as e:
        return {"tool": "pip-audit", "category": "Dependencies", "status": "ERROR", "summary": str(e), "total": 0, "findings": []}


def parse_npm_audit(path: str) -> dict:
    try:
        with open(path) as f:
            data = json.load(f)
        meta = data.get("metadata", {}).get("vulnerabilities", {})
        critical = meta.get("critical", 0)
        high = meta.get("high", 0)
        moderate = meta.get("moderate", 0)
        return {
            "tool": "npm audit", "category": "Dependencies",
            "status": "FAIL" if critical > 0 else ("WARN" if high > 0 else "PASS"),
            "summary": f"Critical: {critical}, High: {high}, Moderate: {moderate}",
            "total": critical + high + moderate,
            "findings": [],
        }
    except Exception as e:
        return {"tool": "npm audit", "category": "Dependencies", "status": "ERROR", "summary": str(e), "total": 0, "findings": []}


def parse_trivy(path: str) -> dict:
    try:
        with open(path) as f:
            data = json.load(f)
        results = data.get("Results", [])
        vulns = []
        for r in results:
            for v in r.get("Vulnerabilities", r.get("Misconfigurations", [])):
                sev = v.get("Severity", "?").upper()
                if sev in ("CRITICAL", "HIGH"):
                    vulns.append({
                        "severity": sev,
                        "file": r.get("Target", "?"),
                        "line": "-",
                        "message": v.get("Title", v.get("Description", ""))[:80],
                        "test": v.get("VulnerabilityID", v.get("ID", "?")),
                    })
        critical = sum(1 for v in vulns if v["severity"] == "CRITICAL")
        high = sum(1 for v in vulns if v["severity"] == "HIGH")
        return {
            "tool": "Trivy", "category": "Infrastructure",
            "status": "FAIL" if critical > 0 else ("WARN" if high > 0 else "PASS"),
            "summary": f"CRITICAL: {critical}, HIGH: {high}",
            "total": len(vulns),
            "findings": vulns[:20],
        }
    except Exception as e:
        return {"tool": "Trivy", "category": "Infrastructure", "status": "ERROR", "summary": str(e), "total": 0, "findings": []}


def parse_licenses(path: str) -> dict:
    BLOCKED = {"GPL-2.0", "GPL-3.0", "AGPL-3.0", "SSPL-1.0", "GPL-2.0-only", "GPL-3.0-only", "AGPL-3.0-only"}
    try:
        with open(path) as f:
            data = json.load(f)
        if isinstance(data, list):
            violations = [p for p in data if any(b in p.get("License", "") for b in BLOCKED)]
            return {
                "tool": "pip-licenses", "category": "License",
                "status": "FAIL" if violations else "PASS",
                "summary": f"{len(data)} packages, {len(violations)} blocked licenses",
                "total": len(data),
                "findings": [
                    {"severity": "HIGH", "file": p.get("Name", "?"), "line": "-",
                     "message": f"Blocked license: {p.get('License','?')}", "test": "license-compliance"}
                    for p in violations
                ],
            }
        return {"tool": "pip-licenses", "category": "License", "status": "PASS", "summary": "No violations", "total": 0, "findings": []}
    except Exception as e:
        return {"tool": "pip-licenses", "category": "License", "status": "ERROR", "summary": str(e), "total": 0, "findings": []}


def parse_coverage(path: str) -> dict:
    import xml.etree.ElementTree as ET
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        rate = float(root.attrib.get("line-rate", 0)) * 100
        branch = float(root.attrib.get("branch-rate", 0)) * 100
        return {
            "tool": "pytest-cov", "category": "Coverage",
            "status": "PASS" if rate >= 70 else "FAIL",
            "summary": f"Line: {rate:.1f}%, Branch: {branch:.1f}%",
            "total": 0,
            "findings": [],
            "metrics": {"line": rate, "branch": branch},
        }
    except Exception as e:
        return {"tool": "pytest-cov", "category": "Coverage", "status": "ERROR", "summary": str(e), "total": 0, "findings": []}


# ── Report discovery ──────────────────────────────────────────────────────

PARSERS = {
    "**/bandit*.json": parse_bandit,
    "**/semgrep*.json": parse_semgrep,
    "**/gitleaks*.json": parse_gitleaks,
    "**/pip-audit*.json": parse_pip_audit,
    "**/npm-audit*.json": parse_npm_audit,
    "**/trivy-*.json": parse_trivy,
    "**/licenses-python.json": parse_licenses,
    "**/coverage.xml": parse_coverage,
}


def collect_reports(reports_dir: str) -> list[dict]:
    results = []
    seen_tools = set()
    for pattern, parser in PARSERS.items():
        for path in glob.glob(os.path.join(reports_dir, "**", os.path.basename(pattern)), recursive=True):
            result = parser(path)
            key = result["tool"]
            if key not in seen_tools:
                seen_tools.add(key)
                result["source_file"] = path
                results.append(result)
    return results


# ── HTML generation ───────────────────────────────────────────────────────

STATUS_COLOUR = {"PASS": "#22c55e", "FAIL": "#ef4444", "WARN": "#f59e0b", "ERROR": "#8b5cf6", "SKIP": "#6b7280"}
STATUS_ICON   = {"PASS": "✓", "FAIL": "✗", "WARN": "⚠", "ERROR": "?", "SKIP": "—"}


def render_findings_table(findings: list) -> str:
    if not findings:
        return "<p style='color:#6b7280;font-size:0.85em'>No findings.</p>"
    rows = ""
    for f in findings:
        sev_col = {"HIGH": "#ef4444", "CRITICAL": "#7f1d1d", "MEDIUM": "#f59e0b", "LOW": "#6b7280"}.get(f.get("severity", ""), "#9ca3af")
        rows += f"""
        <tr>
          <td style='color:{sev_col};font-weight:bold'>{f.get('severity','?')}</td>
          <td style='font-family:monospace;font-size:0.8em'>{f.get('file','?')}</td>
          <td>{f.get('line','?')}</td>
          <td style='font-size:0.85em'>{f.get('message','?')}</td>
          <td style='font-family:monospace;font-size:0.75em;color:#9ca3af'>{f.get('test','?')}</td>
        </tr>"""
    return f"""
    <table style='width:100%;border-collapse:collapse;font-size:0.85em;margin-top:8px'>
      <thead>
        <tr style='background:#1f2937;color:#9ca3af'>
          <th style='padding:4px 8px;text-align:left'>Severity</th>
          <th style='padding:4px 8px;text-align:left'>File/Package</th>
          <th style='padding:4px 8px;text-align:left'>Line</th>
          <th style='padding:4px 8px;text-align:left'>Message</th>
          <th style='padding:4px 8px;text-align:left'>Rule/CVE</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>"""


def generate_html(reports: list[dict], commit: str, branch: str, run_id: str, timestamp: str) -> str:
    total = len(reports)
    passed = sum(1 for r in reports if r["status"] == "PASS")
    failed = sum(1 for r in reports if r["status"] == "FAIL")
    warned = sum(1 for r in reports if r["status"] == "WARN")
    overall = "PASS" if failed == 0 else "FAIL"
    overall_col = STATUS_COLOUR[overall]

    categories = {}
    for r in reports:
        categories.setdefault(r["category"], []).append(r)

    cards_html = ""
    for cat, items in sorted(categories.items()):
        cat_fail = any(i["status"] == "FAIL" for i in items)
        cat_col = "#ef4444" if cat_fail else "#22c55e"
        items_html = ""
        for item in items:
            sc = STATUS_COLOUR.get(item["status"], "#9ca3af")
            si = STATUS_ICON.get(item["status"], "?")
            findings_html = render_findings_table(item.get("findings", []))
            total_findings = item.get("total", 0)
            items_html += f"""
            <div style='background:#111827;border-radius:6px;padding:12px;margin-bottom:8px;border-left:3px solid {sc}'>
              <div style='display:flex;justify-content:space-between;align-items:center'>
                <span style='font-weight:600;color:#f9fafb'>{item['tool']}</span>
                <span style='color:{sc};font-weight:bold'>{si} {item['status']}</span>
              </div>
              <div style='color:#9ca3af;font-size:0.85em;margin-top:4px'>{item['summary']}</div>
              {"" if total_findings == 0 else f"<details style='margin-top:8px'><summary style='cursor:pointer;color:#60a5fa;font-size:0.85em'>{total_findings} finding(s) — click to expand</summary>{findings_html}</details>"}
            </div>"""

        cards_html += f"""
        <div style='margin-bottom:24px'>
          <h3 style='color:{cat_col};font-size:1em;margin:0 0 8px;text-transform:uppercase;letter-spacing:0.05em'>{cat}</h3>
          {items_html}
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>HyperCode — Security & Quality Dashboard</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: #0f172a; color: #e2e8f0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; padding: 24px; }}
    a {{ color: #60a5fa; }}
  </style>
</head>
<body>
  <div style='max-width:960px;margin:0 auto'>

    <!-- Header -->
    <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid #1f2937'>
      <div>
        <h1 style='font-size:1.5em;color:#f8fafc'>HyperCode V2.4</h1>
        <p style='color:#64748b;font-size:0.85em'>Security &amp; Quality Dashboard</p>
      </div>
      <div style='text-align:right'>
        <div style='font-size:2em;font-weight:bold;color:{overall_col}'>{STATUS_ICON[overall]} {overall}</div>
        <div style='color:#64748b;font-size:0.75em'>{timestamp}</div>
      </div>
    </div>

    <!-- Metadata -->
    <div style='display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:24px'>
      <div style='background:#1e293b;border-radius:8px;padding:12px;text-align:center'>
        <div style='font-size:1.75em;font-weight:bold;color:#f8fafc'>{total}</div>
        <div style='color:#64748b;font-size:0.8em'>Scans Run</div>
      </div>
      <div style='background:#1e293b;border-radius:8px;padding:12px;text-align:center'>
        <div style='font-size:1.75em;font-weight:bold;color:#22c55e'>{passed}</div>
        <div style='color:#64748b;font-size:0.8em'>Passed</div>
      </div>
      <div style='background:#1e293b;border-radius:8px;padding:12px;text-align:center'>
        <div style='font-size:1.75em;font-weight:bold;color:#ef4444'>{failed}</div>
        <div style='color:#64748b;font-size:0.8em'>Failed</div>
      </div>
      <div style='background:#1e293b;border-radius:8px;padding:12px;text-align:center'>
        <div style='font-size:1.75em;font-weight:bold;color:#f59e0b'>{warned}</div>
        <div style='color:#64748b;font-size:0.8em'>Warnings</div>
      </div>
    </div>

    <!-- Build info -->
    <div style='background:#1e293b;border-radius:8px;padding:12px;margin-bottom:24px;font-size:0.8em;color:#94a3b8;display:flex;gap:24px'>
      <span>Branch: <strong style='color:#e2e8f0'>{branch}</strong></span>
      <span>Commit: <strong style='color:#e2e8f0;font-family:monospace'>{commit[:12]}</strong></span>
      <span>Run: <strong style='color:#e2e8f0'>{run_id}</strong></span>
    </div>

    <!-- Scan results by category -->
    {cards_html}

    <!-- Footer -->
    <div style='margin-top:32px;padding-top:16px;border-top:1px solid #1f2937;color:#475569;font-size:0.75em;text-align:center'>
      Generated by HyperCode scan pipeline · {timestamp} ·
      Thresholds defined in <code>quality-gate-thresholds.yml</code>
    </div>
  </div>
</body>
</html>"""


# ── Entry point ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate HyperCode scan dashboard")
    parser.add_argument("--reports-dir", default="reports", help="Directory containing scan JSON reports")
    parser.add_argument("--output", default="reports/dashboard.html", help="Output HTML file path")
    parser.add_argument("--commit", default="unknown")
    parser.add_argument("--branch", default="unknown")
    parser.add_argument("--run-id", default="local")
    args = parser.parse_args()

    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    reports = collect_reports(args.reports_dir)

    if not reports:
        print("No scan reports found — generating empty dashboard", file=sys.stderr)

    html = generate_html(reports, args.commit, args.branch, args.run_id, timestamp)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)

    failed = sum(1 for r in reports if r["status"] == "FAIL")
    print(f"Dashboard generated: {args.output} ({len(reports)} scans, {failed} failures)")

    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
