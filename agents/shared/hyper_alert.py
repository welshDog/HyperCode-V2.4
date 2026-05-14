"""
hyper_alert.py — Fleet-wide Discord alert helper for HyperCode V2.4 agents.

Any agent can import this and fire a secrets-safe Discord alert in 1 line:

    from shared.hyper_alert import HyperAlert
    await HyperAlert.warn("disk-full", "Disk at 95%", fields=[...])

Secrets rules (NEVER break these):
  - Webhook URL comes from DISCORD_ALERTS_WEBHOOK_URL env var ONLY.
  - URL is NEVER logged, printed, or returned in any response.
  - No container secrets, tokens, or env values are ever sent to Discord.
  - If env var is missing, all alerts are silently skipped (warn in logs only).

Available alert levels:
  HyperAlert.info(...)    🔵 Blue  — informational, no action needed
  HyperAlert.warn(...)    🟡 Amber — something needs attention soon
  HyperAlert.error(...)   🔴 Red   — something broke / needs immediate action
  HyperAlert.success(...) 🟢 Green — milestone / recovery / good news

Pre-built helpers (one-liner calls):
  HyperAlert.disk_warning(agent, path, used_pct)
  HyperAlert.api_quota(agent, service, used_pct)
  HyperAlert.cert_expiry(domain, days_left)
  HyperAlert.agent_started(agent)
  HyperAlert.agent_recovered(agent)
"""

import asyncio
import logging
import os
from typing import Optional

import aiohttp

logger = logging.getLogger("hyper.alert")

# Loaded once at import — never re-read, never logged.
_WEBHOOK_URL: Optional[str] = os.environ.get("DISCORD_ALERTS_WEBHOOK_URL", "").strip() or None

# Colour palette (matches healer alert colours for visual consistency)
_COLOURS = {
    "info":    0x4488FF,  # 🔵 Blue
    "warn":    0xFF8800,  # 🟡 Amber
    "error":   0xFF4444,  # 🔴 Red
    "success": 0x44BB44,  # 🟢 Green
}

_ICONS = {
    "info":    "🔵",
    "warn":    "⚠️",
    "error":   "🔴",
    "success": "✅",
}


class HyperAlert:
    """
    Static helper — no instance needed.
    Every method is async; await it or fire-and-forget with asyncio.create_task().
    """

    # ------------------------------------------------------------------
    # Core send method
    # ------------------------------------------------------------------

    @staticmethod
    async def send(
        level: str,
        title: str,
        description: str,
        fields: Optional[list] = None,
        footer: Optional[str] = None,
        agent_name: Optional[str] = None,
    ) -> bool:
        """
        Send a Discord embed alert.

        level: 'info' | 'warn' | 'error' | 'success'
        Returns True on success, False on failure / not configured.
        """
        if not _WEBHOOK_URL:
            logger.warning(
                f"[HyperAlert] DISCORD_ALERTS_WEBHOOK_URL not set — alert skipped: {title}"
            )
            return False

        colour = _COLOURS.get(level, _COLOURS["info"])
        icon = _ICONS.get(level, "🔵")
        footer_text = footer or f"HyperCode V2.4{' · ' + agent_name if agent_name else ''}"

        payload = {
            "username": "HyperCode 🐕",
            "embeds": [
                {
                    "title": f"{icon} {title}",
                    "description": description,
                    "color": colour,
                    "fields": fields or [],
                    "footer": {"text": footer_text},
                }
            ],
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    _WEBHOOK_URL,  # never printed or logged
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status in (200, 204):
                        logger.info(f"[HyperAlert] {level.upper()} alert sent: {title}")
                        return True
                    else:
                        logger.error(
                            f"[HyperAlert] Discord returned HTTP {resp.status} for alert: {title}"
                        )
                        return False
        except asyncio.TimeoutError:
            logger.error(f"[HyperAlert] Timeout sending alert: {title}")
            return False
        except Exception as e:
            logger.error(f"[HyperAlert] Unexpected error ({type(e).__name__}) sending alert: {title}")
            return False

    # ------------------------------------------------------------------
    # Level shortcuts
    # ------------------------------------------------------------------

    @classmethod
    async def info(cls, title: str, description: str, **kwargs) -> bool:
        return await cls.send("info", title, description, **kwargs)

    @classmethod
    async def warn(cls, title: str, description: str, **kwargs) -> bool:
        return await cls.send("warn", title, description, **kwargs)

    @classmethod
    async def error(cls, title: str, description: str, **kwargs) -> bool:
        return await cls.send("error", title, description, **kwargs)

    @classmethod
    async def success(cls, title: str, description: str, **kwargs) -> bool:
        return await cls.send("success", title, description, **kwargs)

    # ------------------------------------------------------------------
    # Pre-built fleet alert helpers
    # ------------------------------------------------------------------

    @classmethod
    async def disk_warning(cls, agent_name: str, path: str, used_pct: float) -> bool:
        """
        🟡 Amber: Disk usage is high.
        Example: await HyperAlert.disk_warning('coder-agent', '/data', 92.5)
        """
        level = "error" if used_pct >= 95 else "warn"
        return await cls.send(
            level,
            title="Disk Space Warning",
            description=(
                f"**`{agent_name}`** is reporting high disk usage on `{path}`.\n"
                f"At **{used_pct:.1f}%** used — action needed before the disk fills."
            ),
            fields=[
                {"name": "Agent", "value": f"`{agent_name}`", "inline": True},
                {"name": "Mount", "value": f"`{path}`", "inline": True},
                {"name": "Used", "value": f"**{used_pct:.1f}%**", "inline": True},
                {
                    "name": "What to do",
                    "value": (
                        "1️⃣ `docker exec " + agent_name + " df -h` to see breakdown\n"
                        "2️⃣ `docker system prune -f` to clear build cache\n"
                        "3️⃣ Check log volumes for runaway log files"
                    ),
                    "inline": False,
                },
            ],
            agent_name=agent_name,
        )

    @classmethod
    async def api_quota(cls, agent_name: str, service: str, used_pct: float) -> bool:
        """
        🟡 Amber: API quota is running low.
        Example: await HyperAlert.api_quota('broski-bot', 'OpenAI', 88.0)
        """
        level = "error" if used_pct >= 95 else "warn"
        return await cls.send(
            level,
            title=f"API Quota Warning — {service}",
            description=(
                f"**`{agent_name}`** reports the **{service}** API quota is at **{used_pct:.1f}%**.\n"
                f"Approaching the limit — requests may start failing soon."
            ),
            fields=[
                {"name": "Agent", "value": f"`{agent_name}`", "inline": True},
                {"name": "Service", "value": service, "inline": True},
                {"name": "Quota Used", "value": f"**{used_pct:.1f}%**", "inline": True},
                {
                    "name": "What to do",
                    "value": (
                        "1️⃣ Check the service dashboard for remaining quota\n"
                        "2️⃣ Consider rate-limiting or caching responses\n"
                        "3️⃣ Rotate to a backup key if available"
                    ),
                    "inline": False,
                },
            ],
            agent_name=agent_name,
        )

    @classmethod
    async def cert_expiry(cls, domain: str, days_left: int) -> bool:
        """
        🟡 Amber / 🔴 Red: TLS certificate expiring soon.
        Example: await HyperAlert.cert_expiry('hyperfocuszone.com', 12)
        """
        level = "error" if days_left <= 7 else "warn"
        urgency = "🔴 CRITICAL" if days_left <= 7 else "⚠️ Action Needed"
        return await cls.send(
            level,
            title=f"TLS Certificate Expiring — {domain}",
            description=(
                f"{urgency}: The TLS certificate for **`{domain}`** expires in **{days_left} day(s)**.\n"
                f"HTTPS will fail for all users once it expires."
            ),
            fields=[
                {"name": "Domain", "value": f"`{domain}`", "inline": True},
                {"name": "Days Left", "value": f"**{days_left}**", "inline": True},
                {
                    "name": "What to do",
                    "value": (
                        "1️⃣ Check your cert-manager / Traefik / Nginx logs\n"
                        "2️⃣ Run `certbot renew --dry-run` to test renewal\n"
                        "3️⃣ Force renew: `certbot renew --force-renewal`"
                    ),
                    "inline": False,
                },
            ],
        )

    @classmethod
    async def agent_started(cls, agent_name: str, version: Optional[str] = None) -> bool:
        """
        🟢 Green: Agent came online / recovered.
        Example: await HyperAlert.agent_started('coder-agent', 'v2.4.1')
        """
        desc = f"**`{agent_name}`** has started successfully and is online."
        if version:
            desc += f" Running version `{version}`."
        return await cls.send(
            "success",
            title=f"Agent Online — {agent_name}",
            description=desc,
            agent_name=agent_name,
        )

    @classmethod
    async def agent_recovered(cls, agent_name: str, previous_issue: Optional[str] = None) -> bool:
        """
        🟢 Green: Agent recovered after a crash / OOM / loop.
        Example: await HyperAlert.agent_recovered('coder-agent', 'OOM kill')
        """
        desc = f"**`{agent_name}`** has recovered and is healthy again. 🎉"
        if previous_issue:
            desc += f"\nPrevious issue: *{previous_issue}*"
        return await cls.send(
            "success",
            title=f"Agent Recovered — {agent_name}",
            description=desc,
            agent_name=agent_name,
        )
