# Moved from repo root → scripts/
# Seeds the PostgreSQL database with initial BROski$ data.
# Usage: python scripts/seed_data.py
# Requires: DATABASE_URL set in .env

import os
import sys
from pathlib import Path

# Allow `from app.X import Y` (Sacred Rule: never `from backend.app.X`) —
# app is only importable as a top-level package with backend/ on sys.path.
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

try:
    from app.core.database import engine, Base
    from app.models import user, broski, mission  # noqa: F401
except ImportError as e:
    print(f"⚠️  Import error: {e}")
    print("   Make sure you're running from the repo root with venv active.")
    sys.exit(1)

from sqlalchemy.orm import Session

SEED_USERS = [
    {"username": "broski_admin", "email": "admin@hyperfocus.zone", "is_admin": True},
    {"username": "test_user", "email": "test@hyperfocus.zone", "is_admin": False},
]


def seed():
    print("🌱 Seeding HyperCode database...")
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        # Seed logic here — extend as needed
        print(f"   → Would seed {len(SEED_USERS)} users (extend this file for real data)")

    print("✅ Seed complete!\n")


if __name__ == "__main__":
    seed()
