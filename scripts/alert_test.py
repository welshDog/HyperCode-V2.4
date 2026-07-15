#!/usr/bin/env python3
"""
alert_test.py — Safe HyperAlert routing test.
Fires a single WARN-level Discord alert to confirm the webhook is wired correctly.

Usage:
    python scripts/alert_test.py
    # or via make:
    make alert-test

Requires:
    DISCORD_ALERTS_WEBHOOK_URL env var (or .env file)
"""
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path so shared modules resolve
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agents"))

try:
    from shared.discord_alerts import HyperAlert
except ImportError:
    print("\u274c Could not import HyperAlert from shared.discord_alerts")
    print("   Make sure DISCORD_ALERTS_WEBHOOK_URL is set and the module exists.")
    sys.exit(1)


async def run_test():
    webhook = os.environ.get("DISCORD_ALERTS_WEBHOOK_URL", "")
    if not webhook:
        print("\u26a0\ufe0f  DISCORD_ALERTS_WEBHOOK_URL not set \u2014 alert will be a no-op.")
        print("   Export it or add it to your .env before running alert-test.")

    print("\U0001f4e2 Firing test WARN alert to Discord...")
    await HyperAlert.warn(
        title="\U0001f7e1 HyperAlert Routing Test",
        description="If you see this in Discord, alert routing is \u2705 working!",
        fields=[
            {"name": "source", "value": "make alert-test", "inline": True},
            {
                "name": "env",
                "value": os.environ.get("ENVIRONMENT", "development"),
                "inline": True,
            },
            {
                "name": "timestamp",
                "value": datetime.now(timezone.utc).isoformat(),
                "inline": False,
            },
        ],
    )
    print("\u2705 Alert fired. Check your Discord #alerts channel.")


if __name__ == "__main__":
    asyncio.run(run_test())
