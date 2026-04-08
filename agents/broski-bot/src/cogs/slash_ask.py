# pylint: disable=import-error, no-name-in-module, broad-exception-caught
# pyright: reportMissingImports=false
import time
import discord  # type: ignore
from discord import app_commands  # type: ignore
from discord.ext import commands  # type: ignore

from src.shared.memstream_client import stream_generate  # type: ignore


class SlashAsk(commands.Cog):
    def __init__(self, bot: commands.Bot):
        import os

        self.bot = bot
        self.memstream_url = os.getenv("MEMSTREAM_API_URL", "http://127.0.0.1:8011").strip().rstrip("/")
        self.memstream_token = os.getenv("MEMSTREAM_API_TOKEN", "").strip()

    @app_commands.command(name="ask", description="Ask the local MemStream AI (streams tokens)")
    @app_commands.describe(question="What do you want to ask?")
    async def ask(self, interaction: discord.Interaction, question: str):
        allowed = discord.AllowedMentions.none()

        await interaction.response.defer(thinking=True)

        if not self.memstream_token:
            await interaction.followup.send("MemStream API token missing. Set MEMSTREAM_API_TOKEN.", ephemeral=True)
            return

        current_msg = await interaction.followup.send("Thinking…", wait=True, allowed_mentions=allowed)
        current_text = ""
        last_edit = 0.0
        edit_every_s = 1.0

        async for ev, payload in stream_generate(
            base_url=self.memstream_url,
            token=self.memstream_token,
            prompt=question,
            max_tokens=512,
        ):
            if ev == "error":
                status = payload.get("status")
                if status == 429:
                    await current_msg.edit(content="Busy. Try again in a moment.", allowed_mentions=allowed)
                else:
                    await current_msg.edit(content=f"MemStream error: HTTP {status}", allowed_mentions=allowed)
                return

            if ev == "token":
                delta = payload.get("text") or payload.get("raw") or ""
                current_text += str(delta)

                if len(current_text) > 1900:
                    cut = current_text.rfind("\n", 0, 1900)
                    if cut < 0:
                        cut = current_text.rfind(" ", 0, 1900)
                    if cut < 0:
                        cut = 1900
                    head = current_text[:cut].rstrip()
                    tail = current_text[cut:].lstrip()
                    await current_msg.edit(content=head or "…", allowed_mentions=allowed)
                    current_msg = await interaction.followup.send("…", wait=True, allowed_mentions=allowed)
                    current_text = tail
                    last_edit = time.monotonic()
                    continue

                now = time.monotonic()
                if now - last_edit >= edit_every_s:
                    await current_msg.edit(content=current_text or "…", allowed_mentions=allowed)
                    last_edit = now

            if ev == "done":
                await current_msg.edit(content=current_text or "(no output)", allowed_mentions=allowed)
                return


async def setup(bot: commands.Bot):
    await bot.add_cog(SlashAsk(bot))

