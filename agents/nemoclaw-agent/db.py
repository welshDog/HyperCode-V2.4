"""Async Postgres adapter for nemoclaw-agent.

Stores scan history so the agent can compute deltas (Phase 2 — auto-thinking).
Connection is lazy — if DATABASE_URL is missing, persistence is skipped
silently and /scan still works (in-memory only).
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger("nemoclaw.db")

try:
    import asyncpg
except ImportError:
    asyncpg = None  # type: ignore[assignment]


_pool: "asyncpg.Pool | None" = None


def _database_url() -> str | None:
    url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    if url:
        return url
    # Build from parts if compose provides them
    user = os.getenv("POSTGRES_USER", "hypercode")
    pwd_file = os.getenv("POSTGRES_PASSWORD_FILE")
    pwd = os.getenv("POSTGRES_PASSWORD", "")
    if pwd_file and os.path.exists(pwd_file):
        try:
            with open(pwd_file, "r", encoding="utf-8") as f:
                pwd = f.read().strip()
        except OSError:
            pass
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "hypercode")
    if not pwd:
        return None
    return f"postgresql://{user}:{pwd}@{host}:{port}/{db}"


async def get_pool() -> "asyncpg.Pool | None":
    global _pool
    if asyncpg is None:
        return None
    if _pool is not None:
        return _pool
    url = _database_url()
    if not url:
        logger.info("DATABASE_URL not configured — persistence disabled")
        return None
    try:
        _pool = await asyncpg.create_pool(url, min_size=1, max_size=4, timeout=10)
        return _pool
    except Exception as exc:
        logger.warning("Failed to create pg pool: %s", exc)
        return None


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def insert_scan(
    scan_id: str,
    score: int,
    grade: str,
    counts: dict[str, int],
    total_files: int,
    top_issues: list[dict[str, Any]],
) -> bool:
    pool = await get_pool()
    if pool is None:
        return False
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO code_health_scans
                  (scan_id, score, grade, critical_count, high_count, medium_count, low_count,
                   total_files, top_issues)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb)
                """,
                scan_id,
                score,
                grade,
                counts.get("critical", 0),
                counts.get("high", 0),
                counts.get("medium", 0),
                counts.get("low", 0),
                total_files,
                json.dumps(top_issues),
            )
        return True
    except Exception as exc:
        logger.warning("insert_scan failed: %s", exc)
        return False


async def recent_scans(limit: int = 10) -> list[dict[str, Any]]:
    pool = await get_pool()
    if pool is None:
        return []
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT scan_id, score, grade, critical_count, high_count,
                       medium_count, low_count, total_files, scanned_at
                FROM code_health_scans
                ORDER BY scanned_at DESC
                LIMIT $1
                """,
                limit,
            )
        return [
            {
                "scan_id": str(r["scan_id"]),
                "score": r["score"],
                "grade": r["grade"],
                "counts": {
                    "critical": r["critical_count"],
                    "high": r["high_count"],
                    "medium": r["medium_count"],
                    "low": r["low_count"],
                },
                "total_files": r["total_files"],
                "scanned_at": r["scanned_at"].isoformat(),
            }
            for r in rows
        ]
    except Exception as exc:
        logger.warning("recent_scans failed: %s", exc)
        return []
