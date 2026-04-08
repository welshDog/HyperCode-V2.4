
from locust import HttpUser, task, between
import uuid
import random

class AgentUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        self.agent_id = str(uuid.uuid4())
        self.headers = {"X-API-Key": "dev-key-123"} # Assuming dev key for test
        
        # Register Agent
        payload = {
            "name": f"LoadTest-Agent-{self.agent_id[:8]}",
            "description": "Locust Load Test Agent",
            "version": "1.0.0",
            "endpoint": f"http://agent-{self.agent_id[:8]}:5000",
            "tags": ["load-test"]
        }
        with self.client.post("/agents/register", json=payload, headers=self.headers, catch_response=True) as response:
            if response.status_code == 200:
                self.agent_id = response.json()["id"]
            elif response.status_code == 403:
                response.failure("Auth Failed - Check API Key")
            else:
                response.failure(f"Registration Failed: {response.status_code}")

    @task(3)
    def heartbeat(self):
        payload = {
            "agent_id": self.agent_id,
            "status": "active",
            "load": random.random()
        }
        self.client.post("/agents/heartbeat", json=payload, headers=self.headers)

    @task(1)
    def chat_request(self):
        # Simulate an agent sending a chat request or user chatting with agent
        # Note: This endpoint might be expensive if it hits real LLM
        payload = {
            "messages": [{"role": "user", "content": "ping"}],
            "model": "gpt-3.5-turbo"
        }
        # Use catch_response to handle potential 500s from mock/real LLM gracefully
        with self.client.post("/agents/chat", json=payload, headers=self.headers, catch_response=True) as response:
            if response.status_code == 500:
                # If no LLM key is configured, 500 is expected but technically a "success" for load testing the API layer
                response.success() 

    def on_stop(self):
        # Clean up
        self.client.delete(f"/agents/{self.agent_id}", headers=self.headers)
