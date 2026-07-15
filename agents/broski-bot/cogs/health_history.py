"""
BROski Bot — /health-history cog (NemoClaw Layer 2: Memory)

Shows last 7 scans + delta vs the prior scan. Calls GET /history on
nemoclaw-agent. Read-only — no DB writes from the bot side.
"""
from __future__ import annotations

import os
from datetime import datetime

import discord
import httpx
from discord import app_commands
from discord.ext import commands


GRADE_RANK: dict[str, int] = {"S": 5, "A": 4, "B": 3, "C": 2, "D": 1}
GRADE_COLOURS: dict[str, int] = {
    "S": 0x00FF88,
    "A": 0x00BFFF,
    "B": 0xFFD700,
    "C": 0xFF8C00,
    "D": 0xFF0000,
}


def _read_secret_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def _nemoclaw_url() -> str:
    return os.getenv("NEMOCLAW_URL", "http://nemoclaw-agent:8099").rstrip("/")


def _nemoclaw_api_key() -> str:
    return (
        os.getenv("NEMOCLAW_API_KEY")
        or os.getenv("BOT_API_KEY")
        or _read_secret_file(os.getenv("BOT_API_KEY_FILE", "/run/secrets/api_key"))
        or _read_secret_file("/run/secrets/api_key")
        or ""
    )


def _trend_arrow(curr_grade: str, prev_grade: str | None) -> str:
    if not prev_grade:
        return "•"
    c, p = GRADE_RANK.get(curr_grade, 0), GRADE_RANK.get(prev_grade, 0)
    if c > p:
        return "▲"
    if c < p:
        return "▼"
    return "="


def _fmt_time(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%m-%d %H:%M")
    except (ValueError, TypeError):
        return iso[:16]


def _signed(n: int) -> str:
    return f"+{n}" if n > 0 else str(n)


def _build_embed(scans: list[dict]) -> discord.Embed:
    if not scans:
        embed = discord.Embed(
            title="🧠 NemoClaw History",
            description="No scans recorded yet. Run `/health` to drop the first one.",
            colour=0x808080,
        )
        return embed

    latest = scans[0]
    prior = scans[1] if len(scans) > 1 else None

    grade = str(latest.get("grade", "?"))
    score = int(latest.get("score", 0))
    counts = latest.get("counts") or {}

    colour = GRADE_COLOURS.get(grade, 0x808080)

    # Header — current state + delta vs prior
    if prior:
        score_delta = score - int(prior.get("score", 0))
        prior_grade = str(prior.get("grade", "?"))
        prior_counts = prior.get("counts") or {}
        delta_line = (
            f"**Grade:** {prior_grade} → **{grade}** {_trend_arrow(grade, prior_grade)}  ·  "
            f"**Score:** {prior.get('score', 0)} → **{score}** ({_signed(score_delta)})"
        )
        crit_d = counts.get("critical", 0) - prior_counts.get("critical", 0)
        high_d = counts.get("high", 0) - prior_counts.get("high", 0)
        med_d = counts.get("medium", 0) - prior_counts.get("medium", 0)
        low_d = counts.get("low", 0) - prior_counts.get("low", 0)
        counts_delta = (
            f"🆘 Critical: **{counts.get('critical', 0)}** ({_signed(crit_d)})  ·  "
            f"⚠️ High: **{counts.get('high', 0)}** ({_signed(high_d)})  ·  "
            f"📌 Medium: **{counts.get('medium', 0)}** ({_signed(med_d)})  ·  "
            f"💡 Low: **{counts.get('low', 0)}** ({_signed(low_d)})"
        )
    else:
        delta_line = f"**Grade:** {grade}  ·  **Score:** {score}  ·  *(no prior scan to diff)*"
        counts_delta = (
            f"🆘 Critical: **{counts.get('critical', 0)}**  ·  "
            f"⚠️ High: **{counts.get('high', 0)}**  ·  "
            f"📌 Medium: **{counts.get('medium', 0)}**  ·  "
            f"💡 Low: **{counts.get('low', 0)}**"
        )

    embed = discord.Embed(
        title=f"🧠 NemoClaw History — latest: {grade}",
        description=delta_line,
        colour=colour,
    )
    embed.add_field(name="Latest issue counts", value=counts_delta, inline=False)

    # Table of recent scans
    rows = ["` # | When        | Grade | Score | Files `", "`---|-------------|-------|-------|-------`"]
    for i, scan in enumerate(scans[:7], start=1):
        when = _fmt_time(str(scan.get("scanned_at", "")))
        g = str(scan.get("grade", "?"))
        s = int(scan.get("score", 0))
        f_count = int(scan.get("total_files", 0))
        rows.append(f"` {i} | {when:<11} | {g:<5} | {s:>5} | {f_count:>5} `")

    embed.add_field(name="Recent scans", value="\n".join(rows)[:1024], inline=False)
    embed.set_footer(text=f"NemoClaw • {len(scans)} scan(s) on record • keep chasing the S 🏆")
    return embed


class HealthHistory(commands.Cog):
    """`/health-history` — last 7 scans + delta vs prior."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._url = _nemoclaw_url()
        self._timeout = float(os.getenv("NEMOCLAW_TIMEOUT", "15"))

    @app_commands.command(
        name="health-history",
        description="📊 NemoClaw scan history — last 7 scans + delta vs prior",
    )
    @app_commands.checks.cooldown(1, 30.0, key=lambda i: i.user.id)
    async def health_history(self, interaction: discord.Interaction):
        await interaction.response.defer()

        api_key = _nemoclaw_api_key()
        if not api_key:
            await interaction.followup.send(
                "⚠️ NemoClaw isn't configured — missing API key.",
                ephemeral=True,
            )
            return

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(
                    f"{self._url}/history",
                    params={"limit": 7},
                    headers={"X-API-Key": api_key},
                )
        except httpx.TimeoutException:
            await interaction.followup.send("⏳ NemoClaw timed out.", ephemeral=True)
            return
        except httpx.ConnectError:
            await interaction.followup.send(
                "🔌 NemoClaw is offline. Check `docker compose ps nemoclaw-agent`.",
                ephemeral=True,
            )
            return

        if resp.status_code != 200:
            await interaction.followup.send(
                f"❌ NemoClaw returned {resp.status_code}.",
                ephemeral=True,
            )
            return

        data = resp.json()
        scans = data.get("scans") or []
        embed = _build_embed(scans)
        await interaction.followup.send(embed=embed)

    @health_history.error
    async def _on_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏳ Slow down BROski! Try again in {error.retry_after:.0f}s.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message(
                "💀 Something went sideways. Check logs.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(HealthHistory(bot))
