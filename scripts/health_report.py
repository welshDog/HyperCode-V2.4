#!/usr/bin/env python3
"""
NemoClaw Health Reporter — run from repo root.
  python scripts/health_report.py
  python scripts/health_report.py --webhook   # also POST to Discord webhook
"""
from __future__ import annotations

import ast
import json
import os
import sys
import subprocess
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "agents" / "broski-nemoclaw-agent"))

# Windows UTF-8 fix for stdout + subprocess
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("PYTHONUTF8", "1")

try:
    from analyzer import BROskiAnalyzer, Issue
except ImportError as e:
    print(f"❌ Cannot import BROskiAnalyzer: {e}")
    sys.exit(1)

REPORTS_DIR = ROOT / "reports" / "broski-analysis"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

SKIP_DIRS = frozenset({
    ".git", ".venv", "venv", "__pycache__", "node_modules",
    "backups", "reports", "htmlcov", "tests", ".mypy_cache",
    "k8s", "helm", "docs", ".next", "dist", "build",
})

GRADE_MAP = [
    (95, "S", "LEGENDARY",   0x00FF88, "🏆"),
    (80, "A", "CLEAN",       0x00BFFF, "✅"),
    (65, "B", "GOOD",        0xFFD700, "👍"),
    (50, "C", "NEEDS WORK",  0xFF8C00, "⚠️"),
    (0,  "D", "SOS MODE",    0xFF0000, "🆘"),
]


def grade_for(score: int) -> tuple[str, str, int, str]:
    for threshold, letter, label, colour, emoji in GRADE_MAP:
        if score >= threshold:
            return letter, label, colour, emoji
    return "D", "SOS MODE", 0xFF0000, "🆘"


def ast_scan(root: Path, files: list[Path]) -> list[dict]:
    issues = []
    for fp in files:
        if any(d in fp.parts for d in SKIP_DIRS):
            continue
        try:
            tree = ast.parse(fp.read_text(errors="ignore"))
        except SyntaxError as e:
            issues.append({"file": str(fp.relative_to(root)), "line": e.lineno, "msg": str(e), "severity": "critical"})
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                issues.append({"file": str(fp.relative_to(root)), "line": node.lineno, "msg": "Bare except — catches everything", "severity": "medium"})
    return issues


def _ruff_utf8(root: Path) -> list:
    """Run ruff with explicit UTF-8 encoding — Windows safe."""
    try:
        r = subprocess.run(
            ["ruff", "check", ".", "--output-format", "json"],
            capture_output=True, cwd=root, timeout=120,
            encoding="utf-8", errors="replace",
        )
        import json as _j
        raw = _j.loads(r.stdout or "[]")
        issues = []
        for item in raw:
            loc = item.get("location") or {}
            from analyzer import Issue
            issues.append(Issue(
                file=str(item.get("filename", "")),
                line=int(str(loc.get("row", 0))) if loc.get("row") else None,
                severity="high" if str(item.get("code", "")).startswith(("S", "E9", "F8")) else "medium",
                category=f"lint:{item.get('code','')}",
                message=str(item.get("message", "")),
                auto_fixable=item.get("fix") is not None,
            ))
        return issues
    except Exception as exc:
        print(f"[warn] ruff scan failed: {exc}")
        return []


def run_scan() -> dict:
    analyzer = BROskiAnalyzer(ROOT)
    files = analyzer.py_files()
    ruff_issues = _ruff_utf8(ROOT)
    ast_issues = ast_scan(ROOT, files)

    total = len(ruff_issues) + len(ast_issues)
    score = max(0, min(100, round(100 - (total / max(len(files), 1)) * 40)))
    letter, label, colour, emoji = grade_for(score)

    top_lint = [
        {"file": i.file.replace(str(ROOT) + "/", "").replace(str(ROOT) + "\\", ""), "line": i.line, "msg": i.message[:70]}
        for i in ruff_issues[:5]
    ]
    top_ast = ast_issues[:3]

    report = {
        "score": score,
        "grade": letter,
        "label": label,
        "emoji": emoji,
        "colour": colour,
        "files_scanned": len(files),
        "lint_issues": len(ruff_issues),
        "ast_issues": len(ast_issues),
        "total_issues": total,
        "top_lint": top_lint,
        "top_ast": top_ast,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
    }

    # Save latest
    latest = REPORTS_DIR / "latest.json"
    latest.write_text(json.dumps(report, indent=2))

    return report


def print_report(r: dict) -> None:
    lines = [
        "",
        "══════════════════════════════════════",
        "  🤖 NemoClaw Code Health Report",
        "══════════════════════════════════════",
        f"  Files scanned : {r['files_scanned']}",
        f"  Lint issues   : {r['lint_issues']}",
        f"  AST issues    : {r['ast_issues']}",
        f"  Total issues  : {r['total_issues']}",
        f"  Health Score  : {r['score']}/100",
        f"  Grade         : {r['grade']} — {r['label']} {r['emoji']}",
        "══════════════════════════════════════",
    ]
    if r["top_lint"]:
        lines.append("\nTOP LINT ISSUES:")
        for i in r["top_lint"]:
            lines.append(f"  [LINT] {i['file']}:{i['line']} — {i['msg']}")
    if r["top_ast"]:
        lines.append("\nAST ISSUES:")
        for i in r["top_ast"]:
            lines.append(f"  [AST]  {i['file']}:{i['line']} — {i['msg']}")
    lines.append("")
    print("\n".join(lines))


def post_discord_webhook(r: dict, webhook_url: str) -> None:
    letter, label, colour, emoji = r["grade"], r["label"], r["colour"], r["emoji"]
    score = r["score"]

    top_issues = ""
    for i in (r["top_lint"] + r["top_ast"])[:5]:
        f = i.get("file", "?")
        ln = i.get("line", "?")
        msg = i.get("msg", "")[:55]
        top_issues += f"`{f}:{ln}` — {msg}\n"

    embed = {
        "title": f"{emoji} NemoClaw Health — {letter} | {label}",
        "color": colour,
        "fields": [
            {"name": "Score",   "value": f"**{score}/100**",          "inline": True},
            {"name": "Grade",   "value": f"**{letter} — {label}**",   "inline": True},
            {"name": "Files",   "value": str(r["files_scanned"]),      "inline": True},
            {"name": "Lint",    "value": str(r["lint_issues"]),        "inline": True},
            {"name": "AST",     "value": str(r["ast_issues"]),         "inline": True},
            {"name": "Total",   "value": str(r["total_issues"]),       "inline": True},
        ],
        "footer": {"text": f"HyperCode V2.4 • {r['scanned_at'][:19]}Z"},
    }
    if top_issues:
        embed["fields"].append({"name": "Top Issues", "value": top_issues or "None 🎉", "inline": False})

    payload = json.dumps({"embeds": [embed]}).encode()
    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"✅ Discord webhook posted (HTTP {resp.status})")
    except urllib.error.HTTPError as e:
        print(f"❌ Discord webhook failed: HTTP {e.code}")
    except Exception as e:
        print(f"❌ Discord webhook error: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="NemoClaw Health Reporter")
    parser.add_argument("--webhook", action="store_true", help="Post result to DISCORD_HEALTH_WEBHOOK")
    parser.add_argument("--json", action="store_true", help="Output raw JSON only")
    args = parser.parse_args()

    print("🔍 NemoClaw scanning...") if not args.json else None

    report = run_scan()

    if args.json:
        print(json.dumps(report, indent=2))
        return

    print_report(report)

    if args.webhook:
        webhook = os.getenv("DISCORD_HEALTH_WEBHOOK", "")
        if webhook:
            post_discord_webhook(report, webhook)
        else:
            print("⚠️  DISCORD_HEALTH_WEBHOOK not set — skipping webhook post")

    # Exit non-zero if grade D
    sys.exit(1 if report["grade"] == "D" else 0)


if __name__ == "__main__":
    main()
