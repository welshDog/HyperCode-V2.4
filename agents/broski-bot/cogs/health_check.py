"""
BROski Bot — /health cog (NemoClaw integration)

Calls nemoclaw-agent (sidecar on agents-net) for code-health scans and renders
the grade as a Discord embed. This is the Discord surface for Layer 1 of the
"NemoClaw Alive" architecture.

MVP architecture note: bot → nemoclaw-agent directly via internal agents-net.
Both services share the master API_KEY. Phase 2 will route via Core's One Door
for symmetry with /balance, /daily, etc.
"""
from __future__ import annotations

import os

import discord
import httpx
from discord import app_commands
from discord.ext import commands


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


def _build_embed(data: dict) -> discord.Embed:
    grade = str(data.get("grade", "D"))
    emoji = str(data.get("grade_emoji", "🆘"))
    label = str(data.get("grade_label", "SOS MODE"))
    score = int(data.get("score", 0))
    counts = data.get("counts") or {}
    total_files = int(data.get("total_files", 0))
    targets = data.get("scan_targets") or []
    scan_id = str(data.get("scan_id", ""))[:8]

    colour = GRADE_COLOURS.get(grade, 0xFF0000)
    embed = discord.Embed(
        title=f"{emoji} Code Health — Grade {grade} ({label})",
        description=f"**Score:** `{score}/100`  ·  **Files scanned:** `{total_files}`",
        colour=colour,
    )

    counts_line = (
        f"🆘 Critical: **{counts.get('critical', 0)}**  ·  "
        f"⚠️ High: **{counts.get('high', 0)}**  ·  "
        f"📌 Medium: **{counts.get('medium', 0)}**  ·  "
        f"💡 Low: **{counts.get('low', 0)}**"
    )
    embed.add_field(name="Issue counts", value=counts_line, inline=False)

    if targets:
        embed.add_field(name="Targets", value="`" + "`, `".join(map(str, targets)) + "`", inline=False)

    top = data.get("top_issues") or []
    if top:
        lines: list[str] = []
        for issue in top[:5]:
            sev = str(issue.get("severity", "?")).upper()
            file_ = str(issue.get("file", "?"))
            line = issue.get("line")
            cat = str(issue.get("category", "?"))
            msg = str(issue.get("message", ""))[:80]
            loc = f"{file_}:{line}" if line else file_
            lines.append(f"`{sev}` `{cat}` — {loc}\n    {msg}")
        embed.add_field(name="Top issues", value="\n".join(lines)[:1024], inline=False)

    embed.set_footer(text=f"NemoClaw • scan {scan_id} • chase the S 🏆")
    return embed


class HealthCheck(commands.Cog):
    """Code-health scan via NemoClaw — `/health` slash command."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._url = _nemoclaw_url()
        self._timeout = float(os.getenv("NEMOCLAW_TIMEOUT", "90"))

    @app_commands.command(name="health", description="🏥 Run NemoClaw code-health scan — chase the S grade!")
    @app_commands.checks.cooldown(1, 60.0, key=lambda i: i.user.id)
    async def health(self, interaction: discord.Interaction):
        await interaction.response.defer()

        api_key = _nemoclaw_api_key()
        if not api_key:
            await interaction.followup.send(
                "⚠️ NemoClaw isn't configured — missing API key. Tell Bro to check secrets.",
                ephemeral=True,
            )
            return

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._url}/scan",
                    headers={"X-API-Key": api_key, "Content-Type": "application/json"},
                    json={},
                )
        except httpx.TimeoutException:
            await interaction.followup.send(
                "⏳ NemoClaw scan timed out — codebase too big or container starved. Try again.",
                ephemeral=True,
            )
            return
        except httpx.ConnectError:
            await interaction.followup.send(
                "🔌 NemoClaw is offline. Check `docker compose ps nemoclaw-agent`.",
                ephemeral=True,
            )
            return

        if resp.status_code != 200:
            await interaction.followup.send(
                f"❌ NemoClaw returned {resp.status_code}. Check `docker compose logs nemoclaw-agent`.",
                ephemeral=True,
            )
            return

        data = resp.json()
        embed = _build_embed(data)
        await interaction.followup.send(embed=embed)

    @health.error
    async def _health_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
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
    await bot.add_cog(HealthCheck(bot))
