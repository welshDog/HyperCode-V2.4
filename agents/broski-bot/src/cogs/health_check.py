# pylint: disable=broad-exception-caught
"""
/health — NemoClaw live code health scan for HyperCode V2.4.
Grade chase: S-LEGENDARY → A-CLEAN → B-GOOD → C-NEEDS WORK → D-SOS MODE
"""
from __future__ import annotations

import ast
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands

# Nemoclaw analyzer mounted at /app/nemoclaw_agent in Docker
_NEMOCLAW = Path("/app/nemoclaw_agent")
if _NEMOCLAW.exists():
    sys.path.insert(0, str(_NEMOCLAW))

# Dirs to scan inside the Docker container
_SCAN_ROOTS = [
    Path("/app/backend_src"),      # ./backend
    Path("/app/project_agents"),   # ./agents
]
_SKIP = frozenset({
    "__pycache__", "node_modules", ".venv", "venv",
    "tests", "htmlcov", ".mypy_cache", ".next", "dist", "build",
})

GRADE_MAP = [
    (95, "S", "LEGENDARY",   0x00FF88, "🏆"),
    (80, "A", "CLEAN",       0x00BFFF, "✅"),
    (65, "B", "GOOD",        0xFFD700, "👍"),
    (50, "C", "NEEDS WORK",  0xFF8C00, "⚠️"),
    (0,  "D", "SOS MODE",    0xFF0000, "🆘"),
]
LATEST_JSON = Path("/app/health_reports/latest.json")


def _grade(score: int) -> tuple[str, str, int, str]:
    for threshold, letter, label, colour, emoji in GRADE_MAP:
        if score >= threshold:
            return letter, label, colour, emoji
    return "D", "SOS MODE", 0xFF0000, "🆘"


def _py_files(roots: list[Path]) -> list[Path]:
    files = []
    for root in roots:
        if not root.exists():
            continue
        for f in root.rglob("*.py"):
            if not any(d in f.parts for d in _SKIP):
                files.append(f)
    return files


def _ast_scan(files: list[Path]) -> list[dict]:
    issues = []
    for fp in files:
        try:
            tree = ast.parse(fp.read_text(errors="ignore"))
        except SyntaxError as e:
            issues.append({"file": fp.name, "line": e.lineno, "msg": str(e)[:60]})
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                issues.append({"file": fp.name, "line": node.lineno, "msg": "Bare except"})
    return issues


def _ruff_scan(roots: list[Path]) -> list[dict]:
    import subprocess, json as _json
    paths = [str(r) for r in roots if r.exists()]
    if not paths:
        return []
    try:
        result = subprocess.run(
            ["ruff", "check"] + paths + ["--output-format", "json"],
            capture_output=True, text=True, timeout=60,
        )
        raw = _json.loads(result.stdout)
        out = []
        for item in raw:
            loc = item.get("location") or {}
            out.append({
                "file": Path(item.get("filename", "?")).name,
                "line": loc.get("row"),
                "msg": str(item.get("message", ""))[:65],
            })
        return out
    except Exception:
        return []


def _run_scan() -> dict:
    files = _py_files(_SCAN_ROOTS)
    lint = _ruff_scan(_SCAN_ROOTS)
    ast_issues = _ast_scan(files)
    total = len(lint) + len(ast_issues)
    score = max(0, min(100, round(100 - (total / max(len(files), 1)) * 40)))
    letter, label, colour, emoji = _grade(score)
    return {
        "score": score, "grade": letter, "label": label,
        "colour": colour, "emoji": emoji,
        "files": len(files), "lint": len(lint), "ast": len(ast_issues),
        "total": total,
        "top": (lint + ast_issues)[:5],
        "scanned_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "live": True,
    }


def _load_cached() -> dict | None:
    try:
        if LATEST_JSON.exists():
            return json.loads(LATEST_JSON.read_text())
    except Exception:
        pass
    return None


def _build_embed(r: dict) -> discord.Embed:
    letter, label, colour, emoji = r["grade"], r["label"], r["colour"], r["emoji"]
    score = r["score"]
    source = "live scan" if r.get("live") else f"cached • {r.get('scanned_at','?')}"

    embed = discord.Embed(
        title=f"{emoji}  HyperCode Health  —  {letter}  |  {label}",
        description=f"**Score: {score}/100** • {source}",
        colour=colour,
    )
    embed.add_field(name="📄 Files",  value=str(r["files"]), inline=True)
    embed.add_field(name="🔍 Lint",   value=str(r["lint"]),  inline=True)
    embed.add_field(name="🌳 AST",    value=str(r["ast"]),   inline=True)
    embed.add_field(name="⚠️ Total",  value=str(r["total"]), inline=True)
    embed.add_field(name="🏅 Grade",  value=f"**{letter} — {label}**", inline=True)

    # Progress bar
    filled = round(score / 10)
    bar = "█" * filled + "░" * (10 - filled)
    embed.add_field(name="📊 Health", value=f"`{bar}` {score}%", inline=False)

    if r.get("top"):
        top_text = ""
        for i in r["top"][:5]:
            f = i.get("file", "?")
            ln = i.get("line", "?")
            msg = i.get("msg", "")[:50]
            top_text += f"`{f}:{ln}` {msg}\n"
        embed.add_field(name="🔎 Top Issues", value=top_text or "None! 🎉", inline=False)
    else:
        embed.add_field(name="🎉 Issues", value="Zero issues found!", inline=False)

    # Next grade hint
    hints = {"D": "Fix syntax errors → escape SOS", "C": "Tackle bare excepts → reach B",
             "B": "Clear lint issues → reach A-CLEAN", "A": "Chase that S-LEGENDARY!",
             "S": "S-LEGENDARY! You're the GOAT 🐐"}
    embed.set_footer(text=hints.get(letter, "") + " • /health to rescan")
    return embed


class HealthCheck(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._nemoclaw_ready = _NEMOCLAW.exists()

    @app_commands.command(name="health", description="🏥 Run NemoClaw live code health scan — chase the S grade!")
    async def health(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)

        if not self._nemoclaw_ready:
            # Fall back to cached report
            cached = _load_cached()
            if cached:
                cached["live"] = False
                embed = _build_embed(cached)
                embed.description += "\n⚠️ *Live scan unavailable — showing last cached result*"
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(
                    "❌ NemoClaw not mounted and no cached report found.\n"
                    "Run `make health` from the repo first.",
                    ephemeral=True,
                )
            return

        # Scanning message
        scanning_embed = discord.Embed(
            title="🔍 NemoClaw Scanning...",
            description="Analysing Python files across backend + agents...",
            colour=0x5865F2,
        )
        msg = await interaction.followup.send(embed=scanning_embed, wait=True)

        try:
            report = _run_scan()
        except Exception as e:
            await msg.edit(content=f"❌ Scan failed: {e}", embed=None)
            return

        embed = _build_embed(report)
        await msg.edit(embed=embed)

    @app_commands.command(name="health-last", description="📋 Show last cached NemoClaw health report")
    async def health_last(self, interaction: discord.Interaction) -> None:
        cached = _load_cached()
        if not cached:
            await interaction.response.send_message(
                "No cached report yet. Run `make health` or `/health` first.",
                ephemeral=True,
            )
            return
        cached["live"] = False
        embed = _build_embed(cached)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HealthCheck(bot))
