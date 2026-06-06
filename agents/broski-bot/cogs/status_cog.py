"""
BROski Status Cog
Discord command: !status
Reports live container health from the HyperCode ecosystem.

Sacred Rules:
- discord.py==2.4.0 ONLY (never py-cord)
- Entrypoint: python -u -m cogs.bot
- from app.X import Y (never from backend.app.X)
- 4 spaces indent
"""

import discord
from discord.ext import commands
import subprocess
import json
from datetime import datetime


class StatusCog(commands.Cog):
    """Live HyperCode ecosystem status reporter."""

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="status", aliases=["health", "containers"])
    async def status(self, ctx):
        """Show live status of all HyperCode containers."""
        await ctx.typing()

        embed = discord.Embed(
            title="💚 HyperCode V2.4 — Live Status",
            description="Checking all 48 containers...",
            color=discord.Color.green(),
            timestamp=datetime.utcnow(),
        )

        try:
            result = subprocess.run(
                [
                    "docker", "ps",
                    "--format",
                    "{{.Names}}\t{{.Status}}\t{{.Ports}}",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
            total = len(lines)
            healthy = sum(1 for l in lines if "Up" in l)
            unhealthy = total - healthy

            # Status summary
            status_icon = "🟢" if unhealthy == 0 else "🟡" if unhealthy < 3 else "🔴"
            embed.description = (
                f"{status_icon} **{healthy}/{total} containers running**\n"
                f"Checked at {datetime.utcnow().strftime('%H:%M:%S')} UTC"
            )

            # Show any unhealthy containers
            if unhealthy > 0:
                bad = [l.split("\t")[0] for l in lines if "Up" not in l]
                embed.add_field(
                    name="⚠️ Unhealthy Containers",
                    value="\n".join(f"`{c}`" for c in bad[:10]) or "None",
                    inline=False,
                )
                embed.color = discord.Color.orange()

            # Core services spot check
            core_services = {
                "hypercode-core": ":8000",
                "crew-orchestrator": ":8081",
                "healer-agent": ":8008",
                "redis": ":6379",
                "postgres": ":5432",
                "grafana": ":3001",
            }

            core_status = []
            for name, port in core_services.items():
                is_up = any(name in l and "Up" in l for l in lines)
                icon = "✅" if is_up else "❌"
                core_status.append(f"{icon} `{name}` {port}")

            embed.add_field(
                name="🔑 Core Services",
                value="\n".join(core_status),
                inline=False,
            )

        except subprocess.TimeoutExpired:
            embed.description = "⏰ Docker check timed out."
            embed.color = discord.Color.orange()
        except FileNotFoundError:
            embed.description = "❌ Docker CLI not found. Ensure docker-ce-cli is installed."
            embed.color = discord.Color.red()
        except Exception as e:
            embed.description = f"❌ Error: {e}"
            embed.color = discord.Color.red()

        embed.set_footer(text="BROski♾️ | HyperCode V2.4 | Llanelli, Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁥")
        await ctx.send(embed=embed)

    @commands.command(name="ping")
    async def ping(self, ctx):
        """Check bot latency."""
        latency = round(self.bot.latency * 1000)
        icon = "🟢" if latency < 100 else "🟡" if latency < 250 else "🔴"
        await ctx.send(f"{icon} Pong! `{latency}ms` | BROski♾️ is alive!")

    @commands.command(name="version")
    async def version(self, ctx):
        """Show HyperCode version info."""
        embed = discord.Embed(
            title="🚀 HyperCode Version",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Version", value="v2.4.2", inline=True)
        embed.add_field(name="Containers", value="48", inline=True)
        embed.add_field(name="Bot Library", value="discord.py==2.4.0", inline=True)
        embed.add_field(name="Built in", value="Llanelli, Wales 🏴󠁧󠁢󠁷󠁬󠁳󠁥", inline=False)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(StatusCog(bot))
