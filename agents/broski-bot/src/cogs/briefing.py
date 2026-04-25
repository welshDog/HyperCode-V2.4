from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from src.config.settings import settings

logger = logging.getLogger(__name__)


_MOTIVATION = (
    "Hyperfocus activated. Let's ship. ⚡",
    "Small steps. Big builds. You've got this. 🏴",
    "One task. One win. That's the whole plan. 🎯",
    "Your future users are waiting. Build for them. 🚀",
    "You built 29 containers. Today is just one more step. 🏆",
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
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._session: Optional[aiohttp.ClientSession] = None

    def cog_unload(self) -> None:
        if self._session and not self._session.closed:
            asyncio.create_task(self._session.close())

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=8),
                headers={"Accept": "application/json"},
            )
        return self._session

    async def _fetch_json(self, url: str) -> Optional[dict[str, Any]]:
        try:
            session = await self._get_session()
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, dict):
                        return data
                logger.warning("Briefing fetch failed %s → %d", url, resp.status)
        except Exception as exc:
            logger.warning("Briefing fetch exception (%s): %s", url, exc)
        return None

    @app_commands.command(name="briefing", description="☀️ Morning Briefing — stack + BROski$ + next action")
    async def briefing(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(thinking=True)

        discord_id = str(interaction.user.id)
        now = datetime.now(tz=timezone.utc)
        date_str = now.strftime("%Y-%m-%d")

        health_url = f"{settings.hypercode_core_url}/health"
        balance_url = f"{settings.hypercode_core_url}/api/v1/broski/balance/{discord_id}"

        health_task = asyncio.create_task(self._fetch_json(health_url))
        balance_task = asyncio.create_task(self._fetch_json(balance_url))
        next_up_task = asyncio.to_thread(_read_next_up_from_whats_done, settings.workspace_path)
        last_commit_task = asyncio.to_thread(_get_last_commit_line, settings.workspace_path)

        health, balance, next_up, last_commit = await asyncio.gather(
            health_task,
            balance_task,
            next_up_task,
            last_commit_task,
        )

        stack_ok = bool(health and health.get("status") == "ok")
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
            color=discord.Color.green() if stack_ok else discord.Color.orange(),
        )
        embed.add_field(name="Stack", value=stack_text, inline=False)
        embed.add_field(name="BROski$", value=broski_text, inline=False)
        embed.add_field(name="Next Task", value=next_task_text, inline=False)
        embed.add_field(name="Last Commit", value=last_commit_text, inline=False)

        seed = f"{date_str}:{discord_id}:{os.getenv('ENVIRONMENT','')}"
        embed.set_footer(text=_pick_motivation(seed))

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MorningBriefing(bot))
