"""
BROski Bot — Morning Briefing Cog (Section 7 — ONE TRUE BOT)
Command: /briefing — stack health + BROski$ balance + pulse + next action.

Read-only — every Core read goes via CoreClient. Bot is a pure render
adapter; it decides nothing and persists nothing.

Resurrected 2026-05-22 from agents/broski-bot/src/cogs/briefing.py — the
orphan version imported a dead `src.config.settings` stack and used its own
aiohttp session. Rewired here onto CoreClient (the only sanctioned bridge to
hypercode-core). The WHATS_DONE.md / git-log reads are kept and degrade
gracefully when the workspace is not mounted.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from core_client import CoreClient

logger = logging.getLogger(__name__)


_MOTIVATION = (
    "Hyperfocus activated. Let's ship. ⚡",
    "Small steps. Big builds. You've got this. 🏴",
    "One task. One win. That's the whole plan. 🎯",
    "Your future users are waiting. Build for them. 🚀",
    "You built 30 containers. Today is just one more step. 🏆",
)


def _pick_motivation(seed: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    idx = digest[0] % len(_MOTIVATION)
    return _MOTIVATION[idx]


def _safe_one_line(text: str, max_len: int = 160) -> str:
    cleaned = " ".join(str(text).split())
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 1].rstrip() + "…"


def _workspace_path() -> str:
    """Repo workspace for the WHATS_DONE / git-log reads. Env-driven."""
    return os.getenv("WORKSPACE_PATH") or os.getenv("HC_WORKSPACE") or os.getcwd()


def _read_next_up_from_whats_done(workspace_path: str) -> Optional[str]:
    path = Path(workspace_path) / "WHATS_DONE.md"
    if not path.exists():
        return None

    content = path.read_text(encoding="utf-8", errors="ignore").splitlines()

    start = None
    for i, line in enumerate(content):
        if line.strip().lower().startswith("##") and "next up" in line.lower():
            start = i + 1
            break
    if start is None:
        return None

    for line in content[start:]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            break
        if stripped.startswith("- "):
            return stripped[2:].strip()
        if stripped[0].isdigit() and stripped[1:3] in {". ", ") "}:
            return stripped[3:].strip()
        if stripped[0].isdigit() and stripped[1:2] == ".":
            return stripped[2:].strip()

    return None


def _get_last_commit_line(workspace_path: str) -> Optional[str]:
    try:
        out = subprocess.check_output(
            ["git", "log", "--oneline", "-1"],
            cwd=workspace_path,
            stderr=subprocess.DEVNULL,
        )
        line = out.decode("utf-8", errors="ignore").strip()
        return line or None
    except Exception:
        return None


class MorningBriefing(commands.Cog):
    """☀️ /briefing — a one-glance morning status pull for ADHD flow."""

    def __init__(self, bot: commands.Bot, core: CoreClient) -> None:
        self.bot = bot
        self.core = core

    @staticmethod
    async def _safe(coro):
        """Await a CoreClient call, swallowing any failure to None."""
        try:
            return await coro
        except Exception as exc:  # CoreError or transport error — briefing degrades, never crashes
            logger.warning("Briefing Core read failed: %s", exc)
            return None

    @app_commands.command(name="briefing", description="☀️ Morning Briefing — stack + BROski$ + next action")
    async def briefing(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)

        discord_id = str(interaction.user.id)
        now = datetime.now(tz=timezone.utc)
        date_str = now.strftime("%Y-%m-%d")
        workspace = _workspace_path()

        health, balance, pulse, next_up, last_commit = await asyncio.gather(
            self._safe(self.core.health()),
            self._safe(self.core.get_balance(discord_id)),
            self._safe(self.core.get_pulse()),
            asyncio.to_thread(_read_next_up_from_whats_done, workspace),
            asyncio.to_thread(_get_last_commit_line, workspace),
        )

        stack_ok = bool(health and health.get("status") in ("ok", "healthy"))
        stack_text = "✅ All up" if stack_ok else "⚠️ Issues detected"

        coins = None
        daily_claimed = None
        if balance:
            try:
                coins = int(balance.get("coins"))
            except Exception:
                coins = None
            daily_claimed = balance.get("daily_claimed")

        if coins is None:
            broski_text = "Unavailable (link your Discord → V2.4 account)"
        else:
            daily_str = ""
            if daily_claimed is True:
                daily_str = " · Daily ✅"
            elif daily_claimed is False:
                daily_str = " · Daily ❌"
            broski_text = f"{coins:,} coins{daily_str}"

        next_task_text = _safe_one_line(next_up or "Check WHATS_DONE.md (NEXT UP)")
        last_commit_text = _safe_one_line(last_commit or "No git data available")

        embed = discord.Embed(
            title=f"☀️ Morning Briefing — {date_str}",
            color=discord.Color.green() if stack_ok else discord.Color.red(),
        )
        embed.add_field(name="Stack", value=stack_text, inline=False)
        embed.add_field(name="BROski$", value=broski_text, inline=False)
        if pulse:
            agents_online = pulse.get("agentsOnline")
            user_count = pulse.get("userCount")
            pulse_parts = []
            if isinstance(agents_online, int):
                pulse_parts.append(f"Agents: {agents_online}")
            if isinstance(user_count, int):
                pulse_parts.append(f"Users: {user_count}")
            if pulse_parts:
                embed.add_field(name="Pulse", value=" · ".join(pulse_parts), inline=False)
        embed.add_field(name="Next Task", value=next_task_text, inline=False)
        embed.add_field(name="Last Commit", value=last_commit_text, inline=False)

        seed = f"{date_str}:{discord_id}:{os.getenv('ENVIRONMENT', '')}"
        embed.set_footer(text=_pick_motivation(seed))

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    # CoreClient injected from bot.py
    await bot.add_cog(MorningBriefing(bot, bot.core_client))
