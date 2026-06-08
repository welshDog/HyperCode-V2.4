"""
HyperCode Brain API — Anthropic → Ollama cognitive core.
"""

import os
import requests
from typing import Optional

DEFAULT_MODEL = "claude-sonnet-4-6"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


class BrainAPI:
    """
    HyperCode Brain — Anthropic-powered cognitive core with Ollama fallback.
    Handles all agent queries, self-healing prompts,
    evo pipeline decisions, and real-time search.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        self.anthropic_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.ollama_base = os.getenv("LLM_API_BASE", "http://ollama:11434/v1")
        self.ollama_model = os.getenv("LLM_MODEL", "llama3.2")
        self.model = model

    def query(
        self,
        prompt: str,
        system: str = "You are the HyperCode BROski Brain — a neurodivergent-first AI cognitive core. Be concise, structured, and energetic.",
        temperature: float = 0.7,
    ) -> dict:
        """
        Send a query to the Brain (Anthropic → Ollama fallback).
        Returns a dict with a 'choices' key for backward compatibility.
        """
        if self.anthropic_key:
            headers = {
                "x-api-key": self.anthropic_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.model,
                "max_tokens": 2048,
                "system": system,
                "messages": [{"role": "user", "content": prompt}],
            }
            response = requests.post(ANTHROPIC_API_URL, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            text = data["content"][0]["text"]
            return {"choices": [{"message": {"content": text}}]}

        # Ollama fallback via OpenAI-compat endpoint
        payload = {
            "model": self.ollama_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
        }
        response = requests.post(
            f"{self.ollama_base}/chat/completions",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60,
        )
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
