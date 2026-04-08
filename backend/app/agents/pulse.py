import logging
import requests
from app.agents.brain import brain

logger = logging.getLogger(__name__)

class PulseAgent:
    def __init__(self):
        self.brain = brain
        # Docker internal hostname for Prometheus
        self.prometheus_url = "http://prometheus:9090/api/v1/query"

    async def process(self, payload=None, conversation_id: str | None = None):
        logger.info("[Pulse Specialist] 🏥 Taking the heartbeat of the Swarm...")
        
        # 1. Grab raw vitals from Prometheus (Checking what services are 'up')
        try:
            # Using 'up' query to see which targets are up
            # This query returns status of all scraped targets
            res = requests.get(self.prometheus_url, params={'query': 'up'}, timeout=5)
            if res.status_code == 200:
                raw_data = res.json()
                # Extract relevant info to keep prompt size down
                results = raw_data.get('data', {}).get('result', [])
                simplified_metrics = []
                for result in results:
                    job = result.get('metric', {}).get('job', 'unknown')
                    instance = result.get('metric', {}).get('instance', 'unknown')
                    value = result.get('value', [0, '0'])[1] # '1' is up, '0' is down
                    status = "UP" if value == '1' else "DOWN"
                    simplified_metrics.append(f"Service: {job} ({instance}) -> Status: {status}")
                
                metrics = "\n".join(simplified_metrics) if simplified_metrics else "No active targets found in Prometheus."
            else:
                metrics = f"Error fetching metrics: {res.status_code} - {res.text}"
        except Exception as e:
            metrics = f"CRITICAL: Cannot reach Prometheus! Error: {e}"

        logger.info(f"[Pulse Specialist] Metrics retrieved: {metrics}")

        # 2. Ask the Brain to translate the vitals
        prompt = f"""
        You are the HyperCode Pulse Agent (The Medic). Your job is to read raw Prometheus monitoring metrics and give the developer a quick, punchy, ADHD-friendly health report.

        RULES:
        1. 🏥 Use emojis (✅ for healthy, ⚠️ for warnings, 🔴 for down).
        2. 🧱 Keep it short! 3-4 bullet points max.
        3. 🚫 No PromQL jargon. Translate to plain English (e.g., "The Celery Worker is purring", "The Database is offline").
        4. 🗣️ Talk in a friendly, "co-pilot" tone.

        Here is the raw telemetry data:
        {metrics}
        """
        
        return await self.brain.think(
            "System Medic",
            prompt,
            conversation_id=conversation_id,
            agent_id="pulse",
            memory_mode="self" if conversation_id else "none",
        )

# Global instance
pulse = PulseAgent()
