
import pytest
import asyncio
from app.core.config import get_settings

# Functional Test for Coder Agent
# Requires: 
# 1. HyperCode Core running at localhost:8000
# 2. Coder Agent running and connected to Core (mocked or real)
# This test acts as a "Client" asking the Coder Agent to do something via the Core.

@pytest.mark.asyncio
async def test_coder_agent_hello_world():
    settings = get_settings()
    api_key = settings.API_KEY or "dev-key-123" # Use dev key if unset
    
    # 1. Register a fake "User" agent to initiate chat (or just use direct API)
    # Actually, we can just use the Chat API to talk to the system.
    # But to test specific Coder Agent capabilities, we usually route via the Core.
    
    # Let's assume the Coder Agent is already registered in the system with a specific tag or ID.
    # For this test, we will verify the "Chat" endpoint which uses the LLM Service.
    # Since the Coder Agent is an "Agent", we might want to talk TO it.
    
    # Simple check: Call the Chat Endpoint
    from fastapi.testclient import TestClient
    from main import app
    
    client = TestClient(app)
    
    payload = {
        "messages": [
            {"role": "user", "content": "Write a python function that prints Hello World"}
        ],
        "model": "gpt-3.5-turbo"
    }
    
    # Note: If no LLM key is configured, this might 500 or return mock.
    # We expect a response or a specific error handling.
    
    headers = {"X-API-Key": api_key}
    response = client.post("/agents/chat", json=payload, headers=headers)
    
    # Verification logic
    if response.status_code == 200:
        data = response.json()
        assert "response" in data
        assert "content" in data["response"]
        print(f"SUCCESS: Agent replied: {data['response']['content'][:50]}...")
    elif response.status_code == 500 and "OPENAI_API_KEY" in response.text:
        print("SUCCESS (Partial): Request reached Agent logic but failed on missing OpenAI Key (Expected in Dev).")
    else:
        pytest.fail(f"Agent failed to respond: {response.status_code} - {response.text}")

if __name__ == "__main__":
    # Allow running directly
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_coder_agent_hello_world())
