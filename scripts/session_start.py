import os
from datetime import datetime

SACRED_RULES = """
╔══════════════════════════════════════╗
║     🔥 SACRED RULES LOADED 🔥       ║
╚══════════════════════════════════════╝

✔ docker-ce-cli — NEVER docker.io
✔ from app.X import Y — NEVER from backend.app.X
✔ .env files — NEVER committed to git
✔ Stripe webhook — rate-limit EXEMPT always
✔ Python indent — 4 spaces ONLY
✔ Redis DB1=cache, DB2=rate limits NEVER mix
✔ npm run dev:frontend NOT npm run dev
✔ broski-bot — discord.py==2.4.0 ONLY
✔ Bot entrypoint — python -u -m cogs.bot ONLY
"""

WHATS_DONE = "WHATS_DONE.md"

date = datetime.now().strftime("%Y-%m-%d %H:%M")

print(f"\n🚀 HyperFocus Z0ne Session Started — {date}")
print(SACRED_RULES)

if os.path.exists(WHATS_DONE):
    print(f"📋 WHATS_DONE.md found — check it before building anything!\n")
else:
    print(f"⚠️  No WHATS_DONE.md found — create one before starting!\n")
