# Moved from repo root → examples/
# This file demonstrates a basic HyperCode API connection pattern.
# See docs/API.md for full endpoint reference.

import os
import httpx

BASE_URL = os.getenv("HYPERCODE_API_URL", "http://localhost:8000")
API_KEY = os.getenv("HYPERCODE_API_KEY", "")

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


def get_health() -> dict:
    """Check if the HyperCode API is alive."""
    with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
        resp = client.get("/health")
        resp.raise_for_status()
        return resp.json()


def get_wallet(user_id: int) -> dict:
    """Fetch BROski$ wallet for a user."""
    with httpx.Client(base_url=BASE_URL, headers=HEADERS, timeout=10) as client:
        resp = client.get(f"/api/v1/broski/wallet", params={"user_id": user_id})
        resp.raise_for_status()
        return resp.json()


if __name__ == "__main__":
    print("🔗 Connecting to HyperCode API...")
    health = get_health()
    print(f"✅ Status: {health}")
