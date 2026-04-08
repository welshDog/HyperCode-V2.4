"""
🧠 HyperCode Brain API — Perplexity Agent Integration
Powered by Perplexity AI Agent API
Author: BROski Brain 🦅 | HyperCode V2.0
Date: 2026-03-12
"""

import os
import requests
from typing import Optional

PERPLEXITY_API_URL = "https://api.perplexity.ai/chat/completions"
DEFAULT_MODEL = "llama-3.1-sonar-large-128k-online"


class BrainAPI:
    """
    HyperCode Brain — Perplexity-powered cognitive core.
    Handles all agent queries, self-healing prompts,
    evo pipeline decisions, and real-time search.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        self.api_key = api_key or os.getenv("PERPLEXITY_API_KEY")
        self.model = model
        if not self.api_key:
            raise ValueError("❌ PERPLEXITY_API_KEY not set! Add it to your .env file.")

    def query(
        self,
        prompt: str,
        system: str = "You are the HyperCode BROski Brain — a neurodivergent-first AI cognitive core. Be concise, structured, and energetic.",
        temperature: float = 0.7,
    ) -> dict:
        """
        Send a query to the Perplexity Brain API.
        Returns full response dict including citations.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "return_citations": True,
            "return_related_questions": True,
        }
        response = requests.post(PERPLEXITY_API_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_answer(self, prompt: str, **kwargs) -> str:
        """Quick helper — returns just the text answer."""
        result = self.query(prompt, **kwargs)
        return result["choices"][0]["message"]["content"]

    def healer_query(self, error_log: str) -> str:
        """Healer Agent integration — diagnose and fix errors."""
        prompt = f"""You are an expert DevOps engineer.
        Analyse this error log and provide a fix:
        ---
        {error_log}
        ---
        Give: 1) Root cause 2) Exact fix command 3) Prevention tip."""
        return self.get_answer(prompt)

    def agent_x_task(self, task: str) -> str:
        """Agent X — meta-architect task delegation."""
        prompt = f"""You are Agent X, HyperCode's meta-architect.
        Design the implementation plan for:
        {task}
        Output: Step-by-step agent deployment plan."""
        return self.get_answer(prompt)

    def evo_pipeline_decision(self, agent_name: str, metrics: str) -> str:
        """DevOps Evo Agent — decide if agent needs upgrade."""
        prompt = f"""Agent: {agent_name}\nMetrics: {metrics}
        Should this agent be upgraded? Respond with:
        - Decision: YES/NO
        - Reason: (one line)
        - Suggested upgrade: (if YES)"""
        return self.get_answer(prompt)


# === Quick usage example ===
if __name__ == "__main__":
    brain = BrainAPI()
    print(brain.get_answer("What is the best way to structure a FastAPI microservice?"))
