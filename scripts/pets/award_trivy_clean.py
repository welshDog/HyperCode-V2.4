import json
import os
import sys


def _count_critical(report: dict) -> int:
    total = 0
    results = report.get("Results") or []
    for res in results:
        vulns = res.get("Vulnerabilities") or []
        for v in vulns:
            if str(v.get("Severity", "")).upper() == "CRITICAL":
                total += 1
    return total


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: award_trivy_clean.py <path_to_trivy_json>")
    path = sys.argv[1]
    with open(path, "r", encoding="utf-8") as f:
        report = json.load(f)
    critical = _count_critical(report)
    if critical != 0:
        raise SystemExit(f"CRITICAL vulnerabilities found: {critical}")
    os.execv(sys.executable, [sys.executable, "scripts/pets/award_xp.py", "100", "Trivy 0 CRITICAL", "trivy_local"])


if __name__ == "__main__":
    main()
