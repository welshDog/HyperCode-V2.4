#!/usr/bin/env python3
"""BROski Analyzer — autonomous code health scanner for HyperCode V2.0."""
from __future__ import annotations

import ast
import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("broski.analyzer")

# Typed alias for raw JSON objects from ruff / detect-secrets
_JsonObj = dict[str, object]


@dataclass
class Issue:
    """Represents a single code issue found during a scan."""

    file: str
    line: int | None
    severity: str
    category: str
    message: str
    auto_fixable: bool = False

    def to_dict(self) -> dict[str, object]:
        """Return issue as a plain dict for JSON serialisation."""
        return {
            "file": self.file,
            "line": self.line,
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "auto_fixable": self.auto_fixable,
        }


_SKIP: frozenset[str] = frozenset({
    ".git", ".venv", "venv", "__pycache__",
    "node_modules", "backups", "reports", "htmlcov",
})


class BROskiAnalyzer:
    """Autonomous code analysis engine — ruff, secrets, AST checks."""

    def __init__(self, scan_root: str | Path) -> None:
        """Initialise with the repo root path."""
        self.root: Path = Path(scan_root)
        self.out: Path = self.root / "reports" / "broski-analysis"

    def py_files(self) -> list[Path]:
        """Return all Python files, skipping noise dirs."""
        return [
            f for f in self.root.rglob("*.py")
            if not any(d in f.parts for d in _SKIP)
        ]

    def run(self, args: list[str]) -> tuple[int, str]:
        """Run a subprocess command and return (returncode, stdout)."""
        try:
            r = subprocess.run(
                args, capture_output=True, text=True,
                cwd=self.root, timeout=120, check=False,
            )
            return r.returncode, r.stdout
        except FileNotFoundError as e:
            logger.error("Command %s not found: %s", args, e)
            return -1, ""
        except subprocess.TimeoutExpired as e:
            logger.error("Command %s timed out: %s", args, e)
            return -1, ""
        except Exception as e:  # noqa: BLE001
            logger.error("Command %s failed: %s", args, e)
            return -1, ""

    def ruff(self) -> list[Issue]:
        """Run ruff linter and return issues."""
        rc, out = self.run(["ruff", "check", ".", "--output-format", "json"])
        if rc == -1:
            return []
        try:
            raw: list[_JsonObj] = json.loads(out)
            issues: list[Issue] = []
            for item in raw:
                code = str(item.get("code") or "")
                loc = item.get("location")
                loc_dict: _JsonObj = loc if isinstance(loc, dict) else {}
                row = loc_dict.get("row")
                issues.append(Issue(
                    file=str(item.get("filename") or ""),
                    line=int(str(row)) if row is not None else None,
                    severity="high" if code.startswith(("S", "E9", "F8")) else "medium",
                    category=f"lint:{code}",
                    message=str(item.get("message") or ""),
                    auto_fixable=item.get("fix") is not None,
                ))
            return issues
        except Exception:  # noqa: BLE001
            return []

    def secrets(self) -> list[Issue]:
        """Run detect-secrets and return any credential issues found."""
        rc, out = self.run(["detect-secrets", "scan"])
        if rc == -1:
            return []
        try:
            raw_data: object = json.loads(out)
            if not isinstance(raw_data, dict):
                return []
            data: _JsonObj = raw_data
            if "results" not in data:
                logger.warning("detect-secrets output missing 'results' key — skipping")
                return []
            raw_results = data["results"]
            if not isinstance(raw_results, dict):
                return []
            results: dict[str, object] = raw_results
            issues: list[Issue] = []
            for fname, raw_hits in results.items():
                if not isinstance(raw_hits, list):
                    continue
                for raw_h in raw_hits:
                    if not isinstance(raw_h, dict):
                        continue
                    h: _JsonObj = raw_h
                    ln = h.get("line_number")
                    issues.append(Issue(
                        file=fname,
                        line=int(str(ln)) if ln is not None else None,
                        severity="critical",
                        category="secret:detected",
                        message=f"Secret type: {h.get('type', 'unknown')}",
                    ))
            return issues
        except json.JSONDecodeError as e:
            logger.error("detect-secrets JSON parse failed: %s", e)
            return []
        except Exception as e:  # noqa: BLE001
            logger.error("detect-secrets scan failed unexpectedly: %s", e)
            return []

def ast_check(self, files: list[Path]) -> list[Issue]:
    """Walk AST of each file, flagging bare excepts and syntax errors."""
    issues: list[Issue] = []
    for fp in files:
        try:
            tree = ast.parse(fp.read_text(errors="ignore"))
        except SyntaxError as e:
            issues.append(Issue(
                file=str(fp.relative_to(self.root)),
                line=e.lineno,
                severity="critical",
                category="syntax:error",
                message=str(e),
            ))
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                issues.append(Issue(
                    file=str(fp.relative_to(self.root)),
                    line=node.lineno,
                    severity="medium",
                    category="bare_except",
                    message="Bare except: catches everything",
                    auto_fixable=True,
                ))
    return issues

