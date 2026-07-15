"""
BROski Bot — Layer 3 Voice (NemoClaw speaks unprompted)

Background loop calls Core's `codehealth.pulse` One Door action on a cadence.
Core runs the scan + decides if the move is worth announcing; the bot only
posts the resulting embed to the configured channel. Sacred Rule preserved —
bot is a pure UI adapter, Core is the brain.

Also exposes `/health-pulse` (admin) to trigger a pulse on demand.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands, tasks

from core_client import CoreClient, CoreError, render_to_embed


def _channel_id() -> int:
    try:
        return int(os.getenv("CODE_HEALTH_CHANNEL_ID", "0"))
    except ValueError:
        return 0


def _pulse_hours() -> float:
    try:
        return max(1.0, float(os.getenv("NEMOCLAW_PULSE_HOURS", "24")))
    except ValueError:
        return 24.0


class CodeHealthVoice(commands.Cog):
    """Autonomous code-health announcements via Core's One Door."""

    def __init__(self, bot: commands.Bot, core: CoreClient):
        self.bot = bot
        self.core = core
        self._channel_id = _channel_id()
        self._last_posted_scan_id: str | None = None
        self.pulse_loop.change_interval(hours=_pulse_hours())

    async def cog_load(self):
        if self._channel_id:
            self.pulse_loop.start()

    async def cog_unload(self):
        self.pulse_loop.cancel()

    def _ctx(self, *, manual: bool) -> dict:
        # Auto pulse: date-keyed so a double-fire within a day is idempotent.
        # Manual pulse: unique so testing always gets a fresh scan.
        if manual:
            iid = f"codehealth-pulse-manual-{uuid.uuid4().hex[:12]}"
        else:
            iid = f"codehealth-pulse-{datetime.now(timezone.utc).date().isoformat()}"
        return {
            "user_id": "system",
            "username": "nemoclaw",
            "guild_id": None,
            "channel_id": str(self._channel_id) if self._channel_id else None,
            "interaction_id": iid,
        }

    async def _run_pulse(self, *, manual: bool) -> tuple[bool, str, discord.Embed | None]:
        """Returns (posted, reason, embed)."""
        try:
            resp = await self.core.action("codehealth.pulse", self._ctx(manual=manual))
        except CoreError as e:
            return False, f"core_error:{e.code}", None

        data = resp.get("data") or {}
        should_post = bool(data.get("should_post"))
        reason = str(data.get("reason", "unknown"))
        scan_id = data.get("scan_id")
        embed = render_to_embed(resp["render"]) if resp.get("render") else None

        if not should_post:
            return False, reason, embed

        # Dedup guard — don't re-post the same scan if the loop double-fires.
        if scan_id and scan_id == self._last_posted_scan_id:
            return False, "duplicate_scan", embed

        channel = self.bot.get_channel(self._channel_id) if self._channel_id else None
        if channel is None:
            return False, "channel_missing", embed

        if embed is not None:
            await channel.send(embed=embed)
            self._last_posted_scan_id = scan_id
            return True, reason, embed

        return False, "no_render", embed

    @tasks.loop(hours=24)
    async def pulse_loop(self):
        await self._run_pulse(manual=False)

    @pulse_loop.before_loop
    async def _before_pulse(self):
        await self.bot.wait_until_ready()

    @app_commands.command(
        name="health-pulse",
        description="🔊 Trigger a NemoClaw code-health pulse now (admin)",
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def health_pulse(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if not self._channel_id:
            await interaction.followup.send(
                "⚠️ `CODE_HEALTH_CHANNEL_ID` not set — nowhere to post.",
                ephemeral=True,
            )
            return

        posted, reason, embed = await self._run_pulse(manual=True)
        if posted:
            await interaction.followup.send(
                f"✅ Pulse posted to <#{self._channel_id}> (reason: `{reason}`).",
                ephemeral=True,
            )
        elif embed is not None:
            await interaction.followup.send(
                content=f"🟰 No announcement (reason: `{reason}`). Current state:",
                embed=embed,
                ephemeral=True,
            )
        else:
            await interaction.followup.send(
                f"⚠️ Pulse did not post (reason: `{reason}`).",
                ephemeral=True,
            )

    @health_pulse.error
    async def _on_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "🔒 Manage Server permission required.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "💀 Pulse failed. Check logs.", ephemeral=True
            )


async def setup(bot: commands.Bot):
    await bot.add_cog(CodeHealthVoice(bot, bot.core_client))
