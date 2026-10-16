#!/usr/bin/env python3
"""Vendor agents/shared/secret_env.py:read_secret into every agent file that reads an API key.

Agents ship as isolated images/dirs, so they cannot all import the shared helper. Instead the canonical function
is COPIED between marker comments into each target file, and this tool keeps the copies identical:

    python scripts/vendor_secret_env.py          # insert / refresh the block in every target
    python scripts/vendor_secret_env.py --check  # exit 1 if any copy is missing or has drifted (CI / tests)

A new target = add its path to TARGETS below. Never hand-edit between the markers.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CANONICAL = REPO / "agents" / "shared" / "secret_env.py"
BEGIN = "# >>> vendored from agents/shared/secret_env.py - edit there, then run scripts/vendor_secret_env.py >>>"
END = "# <<< vendored from agents/shared/secret_env.py <<<"

# Files whose key reads go through the vendored read_secret().
TARGETS = [
    "08-project-strategist/agent.py",
    "08-project-strategist/base_agent.py",
    "09-tips-tricks-writer/base_agent.py",
    "brain/base_agent.py",
    "broski-coo/main.py",
    "broski-pets-bridge/main.py",
    "business/base_agent.py",
    "coder/main.py",
    "crew-orchestrator/main.py",
    "crew-orchestrator/safety_client.py",
    "crew-orchestrator/safety_gate.py",
    "fleet-controller/ledger_client.py",
    "fleet-controller/safety_client.py",
    "governor/shepherd_client.py",
    "healer/main.py",
    "meta-research-architect/config.py",
    "mission-director/ledger_client.py",
    "nemoclaw-agent/main.py",
    "safety-shepherd/safety_shepherd.py",
    "super-hyper-broski-agent/main.py",
    "test-agent/main.py",
    "throttle-agent/main.py",
]


def canonical_function() -> str:
    src = CANONICAL.read_text(encoding="utf-8")
    for node in ast.parse(src).body:
        if isinstance(node, ast.FunctionDef) and node.name == "read_secret":
            return ast.get_source_segment(src, node)
    raise SystemExit("read_secret not found in " + str(CANONICAL))


def render_block() -> str:
    return "\n".join([BEGIN, canonical_function(), END])


def _has_import(node: ast.AST) -> bool:
    return any(isinstance(n, (ast.Import, ast.ImportFrom)) for n in ast.walk(node))


def insertion_line(tree: ast.Module, path: str) -> int:
    """1-based line AFTER which the block goes: the end of the last import-ish top-level statement that comes before
    the first def/class. Requires a top-level `import os` before that point (the function uses os)."""
    last = None
    saw_os = False
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            break
        if isinstance(node, ast.Import) and any(a.name == "os" for a in node.names):
            saw_os = True
        if isinstance(node, (ast.Import, ast.ImportFrom)) or (isinstance(node, (ast.Try, ast.If)) and _has_import(node)):
            last = node.end_lineno
    if last is None or not saw_os:
        raise SystemExit(f"{path}: need a top-level `import os` before the first def/class to place the block")
    return last


def process(rel: str, check: bool) -> str:
    """Return 'ok' | 'updated' | 'inserted' (or 'stale'/'missing' in check mode)."""
    path = REPO / "agents" / rel
    raw = path.read_bytes().decode("utf-8")
    nl = "\r\n" if "\r\n" in raw else "\n"
    text = raw.replace("\r\n", "\n")
    block = render_block()
    if BEGIN in text and END in text:
        start = text.index(BEGIN)
        end = text.index(END) + len(END)
        if text[start:end] == block:
            return "ok"
        if check:
            return "stale"
        new = text[:start] + block + text[end:]
        status = "updated"
    else:
        if check:
            return "missing"
        lines = text.split("\n")
        after = insertion_line(ast.parse(text), rel)
        lines[after:after] = ["", block, ""]
        new = "\n".join(lines)
        status = "inserted"
    ast.parse(new)  # never write a file that does not parse
    path.write_bytes(new.replace("\n", nl).encode("utf-8"))
    return status


def main(argv: list[str]) -> int:
    check = "--check" in argv
    bad = 0
    for rel in TARGETS:
        status = process(rel, check)
        print(f"{status:9} agents/{rel}")
        if status in ("stale", "missing"):
            bad += 1
    if check and bad:
        print(f"\n{bad} file(s) out of sync - run: python scripts/vendor_secret_env.py")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
