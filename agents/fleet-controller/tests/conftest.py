import os
import sys

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Add parent directory to path to import main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest_asyncio.fixture
async def client():
    import main

    async with AsyncClient(transport=ASGITransport(app=main.app), base_url="http://test") as ac:
        yield ac
