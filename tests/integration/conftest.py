"""
Integration Test Fixtures
Uses httpx for async HTTP + environment variables for service URLs.
"""
import os
import sys

import httpx
import pytest_asyncio


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../..", "backend"))

CORE_BASE_URL = os.getenv("CORE_BASE_URL", "http://localhost:8000")
HEALER_BASE_URL = os.getenv("HEALER_BASE_URL", "http://localhost:8008")
DASHBOARD_BASE_URL = os.getenv("DASHBOARD_BASE_URL", "http://localhost:8088")


@pytest_asyncio.fixture(scope="function")
async def core_client() -> httpx.AsyncClient:
    async with httpx.AsyncClient(base_url=CORE_BASE_URL, timeout=10.0) as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def healer_client() -> httpx.AsyncClient:
    async with httpx.AsyncClient(base_url=HEALER_BASE_URL, timeout=10.0) as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def dashboard_client() -> httpx.AsyncClient:
    async with httpx.AsyncClient(base_url=DASHBOARD_BASE_URL, timeout=10.0) as client:
        yield client
