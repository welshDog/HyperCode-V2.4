"""
discord_notifier.py — Secrets-safe Discord webhook alerts for healer-agent.

Rules (NEVER break these):
  - Webhook URL is read from DISCORD_OOM_WEBHOOK_URL env var only.
  - The URL is NEVER logged, printed, or included in any response body.
  - If the env var is missing, alerts are silently skipped (warn in logs only).
  - No container secrets or env values are ever sent to Discord.
"""

import asyncio
import logging
import os
from typing import Optional

import aiohttp

logger = logging.getLogger("healer.discord")

# Loaded once at import time — never re-read, never logged.
_WEBHOOK_URL: Optional[str] = os.environ.get("DISCORD_OOM_WEBHOOK_URL", "").strip() or None


class DiscordNotifier:
    """Sends structured OOM kill alerts to a Discord channel via webhook."""

    def __init__(self) -> None:
        if not _WEBHOOK_URL:
            logger.warning(
                "DISCORD_OOM_WEBHOOK_URL not set — OOM Discord alerts are disabled. "
                "Set this env var to enable them."
            )

    async def send_oom_alert(
        self,
        container_name: str,
        exit_code: int,
        restart_count: int,
    ) -> bool:
        """
        Post an OOM kill alert embed to Discord.
        Returns True on success, False on failure or if webhook not configured.
        NEVER logs or exposes the webhook URL.
        """
        if not _WEBHOOK_URL:
            logger.warning(
                f"OOM kill on '{container_name}' (exit {exit_code}, restarts: {restart_count}) — "
                "Discord alert skipped (no webhook configured)."
            )
            return False

        payload = {
            "username": "HyperHealer 🛡️",
            "avatar_url": "https://raw.githubusercontent.com/welshDog/HyperCode-V2.4/main/.github/healer-avatar.png",
            "embeds": [
                {
                    "title": "🔴 OOM Kill Detected",
                    "description": (
                        f"Container **`{container_name}`** was killed by the Linux OOM killer.\n"
                        f"The box ran out of memory and sacrificed this container to survive."
                    ),
                    "color": 0xFF4444,  # Red
                    "fields": [
                        {
                            "name": "Container",
                            "value": f"`{container_name}`",
                            "inline": True,
                        },
                        {
                            "name": "Exit Code",
                            "value": f"`{exit_code}` (137 = OOM)",
                            "inline": True,
                        },
                        {
                            "name": "Total Restarts",
                            "value": str(restart_count),
                            "inline": True,
                        },
                        {
                            "name": "What to do",
                            "value": (
                                "1️⃣ Check memory limits in `docker-compose.agents.yml`\n"
                                "2️⃣ Run `docker stats` to see current usage\n"
                                "3️⃣ Consider raising the limit or reducing load"
                            ),
                            "inline": False,
                        },
                    ],
                    "footer": {
                        "text": "HyperCode V2.4 — healer-agent · OOM Warden",
                    },
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
                        logger.info(
                            f"OOM alert sent to Discord for container '{container_name}'."
                        )
                        return True
                    else:
                        # Log status code only — never the URL
                        logger.error(
                            f"Discord webhook returned HTTP {resp.status} for OOM alert "
                            f"(container: {container_name})."
                        )
                        return False
        except asyncio.TimeoutError:
            logger.error(
                f"Discord webhook timed out sending OOM alert for '{container_name}'."
            )
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error sending Discord OOM alert for '{container_name}': {type(e).__name__}"
            )
            return False

    async def send_custom_alert(
        self,
        title: str,
        description: str,
        color: int = 0xFFAA00,
        fields: Optional[list] = None,
    ) -> bool:
        """
        Generic alert sender for future use (restart loops, disk full, etc.).
        Same secrets-safety rules apply.
        """
        if not _WEBHOOK_URL:
            logger.warning(f"Discord alert skipped (no webhook): {title}")
            return False

        payload = {
            "username": "HyperHealer 🛡️",
            "embeds": [
                {
                    "title": title,
                    "description": description,
                    "color": color,
                    "fields": fields or [],
                    "footer": {"text": "HyperCode V2.4 — healer-agent"},
                }
            ],
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    _WEBHOOK_URL,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    return resp.status in (200, 204)
        except Exception as e:
            logger.error(f"Discord custom alert failed: {type(e).__name__}")
            return False
