from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _normalize_fail_on(values: str) -> set[str]:
    parts = [p.strip().lower() for p in values.split(",") if p.strip()]
    mapped: set[str] = set()
    for p in parts:
        if p in {"critical", "serious", "moderate", "minor"}:
            mapped.add(p)
            continue
        if p == "high":
            mapped.add("serious")
            continue
        if p == "medium":
            mapped.add("moderate")
            continue
        if p == "low":
            mapped.add("minor")
            continue
        mapped.add(p)
    return mapped


def _load_axe_report(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        if len(data) == 1 and isinstance(data[0], dict):
            return data[0]
        return {"violations": []}
    if isinstance(data, dict):
        return data
    return {"violations": []}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    parser.add_argument("--fail-on", required=True)
    args = parser.parse_args()

    report_path = Path(args.report)
    if not report_path.exists():
        print(f"missing_report={report_path}", file=sys.stderr)
        return 2

    fail_on = _normalize_fail_on(args.fail_on)
    report = _load_axe_report(report_path)
    violations = report.get("violations", []) or []

    counts: dict[str, int] = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0, "unknown": 0}
    blockers: list[dict] = []

    for v in violations:
        if not isinstance(v, dict):
            continue
        impact = (v.get("impact") or "unknown").lower()
        if impact not in counts:
            counts["unknown"] += 1
        else:
            counts[impact] += 1
        if impact in fail_on:
            blockers.append(
                {
                    "id": v.get("id"),
                    "impact": impact,
                    "help": v.get("help"),
                    "nodes": len(v.get("nodes") or []),
                }
            )

    print(
        "axe_summary "
        + " ".join([f"{k}={v}" for k, v in counts.items()])
        + f" fail_on={','.join(sorted(fail_on))}"
    )

    if blockers:
        print("blocking_violations=" + str(len(blockers)))
        for b in blockers[:25]:
            print(json.dumps(b, ensure_ascii=False))
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

