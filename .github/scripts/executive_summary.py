import argparse
import json
import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Counts:
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    unknown: int = 0

    def to_dict(self) -> dict:
        return {
            "critical": self.critical,
            "high": self.high,
            "medium": self.medium,
            "low": self.low,
            "unknown": self.unknown,
        }


def _inc(counts: Counts, severity: str) -> None:
    s = (severity or "").strip().lower()
    if s == "critical":
        counts.critical += 1
    elif s == "high":
        counts.high += 1
    elif s == "medium":
        counts.medium += 1
    elif s == "low":
        counts.low += 1
    else:
        counts.unknown += 1


def load_json(path: Path) -> object | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def sarif_counts(path: Path) -> dict[str, Counts]:
    data = load_json(path)
    if not isinstance(data, dict):
        return {}
    counts_by_tool: dict[str, Counts] = defaultdict(Counts)
    for run in data.get("runs", []) or []:
        tool = (((run or {}).get("tool") or {}).get("driver") or {}).get("name") or path.stem
        rules = {r.get("id"): r for r in (((run or {}).get("tool") or {}).get("driver") or {}).get("rules", []) or []}
        for res in (run or {}).get("results", []) or []:
            rule_id = res.get("ruleId")
            sev = None
            props = (res.get("properties") or {})
            sev = props.get("security-severity") or props.get("severity") or sev
            if not sev and rule_id in rules:
                sev = ((rules[rule_id].get("properties") or {}).get("security-severity")) or sev
            if not sev:
                level = (res.get("level") or "").lower()
                if level in {"error", "warning", "note"}:
                    sev = {"error": "high", "warning": "medium", "note": "low"}[level]
            _inc(counts_by_tool[tool], str(sev or "unknown"))
    return counts_by_tool


def trivy_counts(path: Path) -> Counts:
    data = load_json(path)
    counts = Counts()
    if not isinstance(data, dict):
        return counts
    results = data.get("Results") or []
    for r in results:
        vulns = (r or {}).get("Vulnerabilities") or []
        misconfigs = (r or {}).get("Misconfigurations") or []
        for v in vulns:
            _inc(counts, str((v or {}).get("Severity") or "unknown"))
        for m in misconfigs:
            _inc(counts, str((m or {}).get("Severity") or "unknown"))
    return counts


def pip_audit_counts(path: Path) -> Counts:
    data = load_json(path)
    counts = Counts()
    if not isinstance(data, list):
        return counts
    for v in data:
        aliases = (v or {}).get("aliases") or []
        severity = "unknown"
        for a in aliases:
            if isinstance(a, str) and a.startswith("GHSA-"):
                severity = "high"
                break
        _inc(counts, severity)
    return counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="input_dir", required=True)
    ap.add_argument("--out", dest="output_dir", required=True)
    args = ap.parse_args()

    in_dir = Path(args.input_dir)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    sarif_files = list(in_dir.rglob("*.sarif"))
    json_files = list(in_dir.rglob("*.json"))

    sarif_summary: dict[str, dict] = {}
    for p in sarif_files:
        for tool, c in sarif_counts(p).items():
            sarif_summary.setdefault(tool, Counts())
            base = sarif_summary[tool]
            base.critical += c.critical
            base.high += c.high
            base.medium += c.medium
            base.low += c.low
            base.unknown += c.unknown

    trivy = Counts()
    for p in json_files:
        if p.name.startswith("trivy-") and p.name.endswith(".json"):
            c = trivy_counts(p)
            trivy.critical += c.critical
            trivy.high += c.high
            trivy.medium += c.medium
            trivy.low += c.low
            trivy.unknown += c.unknown

    pip_audit = Counts()
    merged = in_dir / "reports" / "security" / "pip-audit-merged.json"
    if merged.exists():
        pip_audit = pip_audit_counts(merged)

    summary = {
        "repo": os.getenv("GITHUB_REPOSITORY", ""),
        "run_id": os.getenv("GITHUB_RUN_ID", ""),
        "sha": os.getenv("GITHUB_SHA", ""),
        "sarif": {k: v.to_dict() for k, v in sarif_summary.items()},
        "trivy_json": trivy.to_dict(),
        "pip_audit_merged": pip_audit.to_dict(),
    }

    (out_dir / "executive-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = []
    lines.append("# Executive Scan Summary")
    lines.append("")
    lines.append(f"- repo: {summary['repo']}")
    lines.append(f"- sha: {summary['sha']}")
    lines.append("")
    lines.append("## Findings (counts)")
    lines.append("")
    for tool, c in sorted(sarif_summary.items(), key=lambda kv: kv[0].lower()):
        lines.append(f"- {tool}: critical={c.critical}, high={c.high}, medium={c.medium}, low={c.low}, unknown={c.unknown}")
    lines.append(f"- Trivy JSON: critical={trivy.critical}, high={trivy.high}, medium={trivy.medium}, low={trivy.low}, unknown={trivy.unknown}")
    lines.append(f"- pip-audit merged: critical={pip_audit.critical}, high={pip_audit.high}, medium={pip_audit.medium}, low={pip_audit.low}, unknown={pip_audit.unknown}")
    lines.append("")
    lines.append("## Remediation pointers")
    lines.append("")
    lines.append("- Use GitHub Security tab for SARIF-backed findings (file/line + rule guidance where available).")
    lines.append("- For dependency findings, update affected package versions and re-run scans.")
    lines.append("- For container/IaC findings, apply the recommended config change and re-scan.")
    (out_dir / "executive-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
