"""BROski NemoClaw Analyzer — autonomous code-health scanner.

Runs ruff + detect-secrets + AST checks and returns a normalised score + grade.
No secret values are ever surfaced — only counts, file paths, and line numbers.
"""
from __future__ import annotations

import ast
import json
import logging
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("nemoclaw.analyzer")

_JsonObj = dict[str, object]

_SKIP: frozenset[str] = frozenset({
    ".git", ".venv", "venv", "__pycache__",
    "node_modules", "backups", "reports", "htmlcov",
    ".mypy_cache", ".pytest_cache", ".next", "dist", "build",
})

GRADE_TABLE: list[tuple[int, str, str, str]] = [
    (95, "S", "LEGENDARY", "🏆"),
    (80, "A", "CLEAN", "✅"),
    (65, "B", "GOOD", "👍"),
    (50, "C", "NEEDS WORK", "⚠️"),
    (0,  "D", "SOS MODE", "🆘"),
]


@dataclass
class Issue:
    file: str
    line: int | None
    severity: str
    category: str
    message: str
    auto_fixable: bool = False


@dataclass
class ScanResult:
    score: int
    grade: str
    grade_label: str
    grade_emoji: str
    total_files: int
    counts: dict[str, int]
    top_issues: list[dict[str, object]]
    scanned_at: str
    scan_targets: list[str]


def _grade(score: int) -> tuple[str, str, str]:
    for threshold, letter, label, emoji in GRADE_TABLE:
        if score >= threshold:
            return letter, label, emoji
    return "D", "SOS MODE", "🆘"


def _score_from_counts(counts: dict[str, int]) -> int:
    raw = 100.0
    raw -= 10 * counts.get("critical", 0)
    raw -= 3 * counts.get("high", 0)
    raw -= 1 * counts.get("medium", 0)
    raw -= 0.3 * counts.get("low", 0)
    return max(0, min(100, int(round(raw))))


class NemoClaw:
    """Code-health scanner. Read-only — never modifies files."""

    def __init__(self, scan_root: str | Path, scan_targets: list[str] | None = None) -> None:
        self.root: Path = Path(scan_root).resolve()
        # If targets are passed, only scan those subdirs (relative to root)
        self.targets: list[Path] = (
            [self.root / t for t in scan_targets]
            if scan_targets
            else [self.root]
        )

    def _py_files(self) -> list[Path]:
        files: list[Path] = []
        for target in self.targets:
            if not target.exists():
                continue
            for f in target.rglob("*.py"):
                if not any(d in f.parts for d in _SKIP):
                    files.append(f)
        return files

    def _run(self, args: list[str], timeout: int = 120) -> tuple[int, str, str]:
        try:
            r = subprocess.run(
                args, capture_output=True, text=True,
                cwd=str(self.root), timeout=timeout, check=False,
            )
            return r.returncode, r.stdout, r.stderr
        except FileNotFoundError:
            logger.warning("Command not installed: %s", args[0])
            return -1, "", "not_installed"
        except subprocess.TimeoutExpired:
            logger.warning("Command timed out: %s", args)
            return -1, "", "timeout"

    def ruff(self) -> list[Issue]:
        target_args = [str(t.relative_to(self.root)) for t in self.targets if t.exists()]
        if not target_args:
            return []
        rc, out, _err = self._run(["ruff", "check", *target_args, "--output-format", "json"])
        if rc < 0:
            return []
        try:
            raw: list[_JsonObj] = json.loads(out or "[]")
        except json.JSONDecodeError:
            return []
        issues: list[Issue] = []
        for item in raw:
            code = str(item.get("code") or "")
            loc = item.get("location")
            loc_dict: _JsonObj = loc if isinstance(loc, dict) else {}
            row = loc_dict.get("row")
            severity = "high" if code.startswith(("S", "E9", "F8")) else "medium"
            issues.append(Issue(
                file=str(item.get("filename") or ""),
                line=int(str(row)) if row is not None else None,
                severity=severity,
                category=f"lint:{code}",
                message=str(item.get("message") or "")[:200],
                auto_fixable=item.get("fix") is not None,
            ))
        return issues

    def secrets(self) -> list[Issue]:
        """Run detect-secrets. Never surfaces the secret value itself."""
        rc, out, _err = self._run(["detect-secrets", "scan"])
        if rc < 0:
            return []
        try:
            data = json.loads(out or "{}")
        except json.JSONDecodeError:
            return []
        if not isinstance(data, dict):
            return []
        results = data.get("results")
        if not isinstance(results, dict):
            return []
        issues: list[Issue] = []
        for fname, hits in results.items():
            if not isinstance(hits, list):
                continue
            for h in hits:
                if not isinstance(h, dict):
                    continue
                ln = h.get("line_number")
                stype = str(h.get("type", "unknown"))
                issues.append(Issue(
                    file=str(fname),
                    line=int(str(ln)) if ln is not None else None,
                    severity="critical",
                    category="secret:detected",
                    message=f"Possible secret ({stype}) — verify and rotate if real",
                ))
        return issues

    def ast_scan(self, files: list[Path]) -> list[Issue]:
        issues: list[Issue] = []
        for fp in files:
            try:
                tree = ast.parse(fp.read_text(errors="ignore"))
            except SyntaxError as e:
                issues.append(Issue(
                    file=str(fp.relative_to(self.root)) if fp.is_absolute() else str(fp),
                    line=e.lineno,
                    severity="critical",
                    category="syntax:error",
                    message=str(e)[:200],
                ))
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    issues.append(Issue(
                        file=str(fp.relative_to(self.root)) if fp.is_absolute() else str(fp),
                        line=node.lineno,
                        severity="medium",
                        category="bare_except",
                        message="Bare except — catches everything including KeyboardInterrupt",
                        auto_fixable=True,
                    ))
        return issues

    def scan(self) -> ScanResult:
        files = self._py_files()
        all_issues: list[Issue] = []
        all_issues.extend(self.ruff())
        all_issues.extend(self.secrets())
        all_issues.extend(self.ast_scan(files))

        counts: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for issue in all_issues:
            counts[issue.severity] = counts.get(issue.severity, 0) + 1

        score = _score_from_counts(counts)
        letter, label, emoji = _grade(score)

        # Top issues by severity (critical first), max 5
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_issues = sorted(all_issues, key=lambda i: severity_order.get(i.severity, 9))
        top = [asdict(i) for i in sorted_issues[:5]]

        return ScanResult(
            score=score,
            grade=letter,
            grade_label=label,
            grade_emoji=emoji,
            total_files=len(files),
            counts=counts,
            top_issues=top,
            scanned_at=datetime.now(timezone.utc).isoformat(),
            scan_targets=[str(t.relative_to(self.root)) if t.is_absolute() and t != self.root else "." for t in self.targets],
        )
