"""
MAPE-K Bootstrap -- Wire the engine into the Healer Agent on startup.

Usage in agents/healer/main.py lifespan:
    from .mape_k_bootstrap import start_mape_k
    kb = await start_mape_k(app)
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys

# Ensure the healer directory is on sys.path so mape_k_* resolve as flat modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from .mape_k_engine import KnowledgeBase, mape_k_loop, DEFAULT_SERVICES  # noqa: E402
from .mape_k_api import router as mape_k_router, set_knowledge_base  # noqa: E402

logger = logging.getLogger("mape_k_bootstrap")


async def start_mape_k(app: FastAPI, interval: int = 10) -> KnowledgeBase:
    """Bootstrap MAPE-K: create KB, register routes, start background loop."""
    kb = KnowledgeBase()
    set_knowledge_base(kb)

    app.include_router(mape_k_router)
    logger.info("MAPE-K API routes registered at /mape-k/*")

    _ = asyncio.create_task(
        mape_k_loop(
            services=DEFAULT_SERVICES,
            kb=kb,
            interval_seconds=interval,
        )
    )
    logger.info("MAPE-K loop started -- polling every %ss", interval)
    return kb
