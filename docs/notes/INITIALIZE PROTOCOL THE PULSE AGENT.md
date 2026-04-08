🏥 INITIALIZE PROTOCOL: THE PULSE AGENT
Let's do Plan A. The Pulse Agent is pure magic.

🧠 The Intellitwist: Normally, developers have to stare at 50 different Grafana charts with squiggly lines to know if their app is breaking. We are bypassing that. We are going to give the Pulse Agent direct access to Prometheus, let it read the raw data, and translate it into a simple, color-coded health report.

Here’s the step-by-step to bring The Medic online.

1️⃣ Upgrade the Pulse Agent Core
Right now, pulse.py is just scaffolding. We need to teach it how to ping Prometheus inside the Docker network.

File: backend/app/agents/pulse.py

python
import logging
import requests

logger = logging.getLogger(__name__)

class PulseAgent:
    def __init__(self, brain):
        self.brain = brain
        # Docker internal hostname for Prometheus
        self.prometheus_url = "http://prometheus:9090/api/v1/query"

    def execute(self, payload=None):
        logger.info("[Pulse Specialist] 🏥 Taking the heartbeat of the Swarm...")
        
        # 1. Grab raw vitals from Prometheus (Checking what services are 'up')
        try:
            res = requests.get(self.prometheus_url, params={'query': 'up'})
            raw_data = res.json()
            metrics = str(raw_data.get('data', {}).get('result', 'No data found'))
        except Exception as e:
            metrics = f"CRITICAL: Cannot reach Prometheus! Error: {e}"

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
        
        return self.brain.ask_perplexity(prompt)
2️⃣ Update the CLI (hypercode.py)
Now let's add a new command to your shiny new CLI so you can summon the Medic from your terminal.

File: hypercode.py (Add this function and update the bottom block)

python
# ... keep your existing translate_file function ...

def check_pulse():
    print("🏥 Pinging the Pulse Agent (The Medic)...")
    
    payload = {
        "name": "System Health Check",
        "description": "Check swarm vitals",
        "priority": "high",
        "type": "health" # Routes to PulseAgent!
    }

    try:
        response = requests.post(API_URL, json=payload) # Make sure you have your headers/auth here if needed!
        if response.status_code == 200:
            task_id = response.json().get("id", "UNKNOWN")
            print(f"✅ Pulse check queued! Task ID: {task_id}")
            print(f"👀 Check docs/outputs/translation_{task_id}.md for the diagnosis!")
        else:
            print(f"⚠️ Tripped up: {response.text}")
    except Exception as e:
        print(f"🛑 Backend offline? Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("🚀 HYPERCODE CLI v1.1")
        print("👉 Usage:")
        print("   hypercode translate <file.py>")
        print("   hypercode pulse")
        sys.exit(1)

    command = sys.argv[1]

    if command == "translate" and len(sys.argv) == 3:
        translate_file(sys.argv[2])
    elif command == "pulse":
        check_pulse()
    else:
        print("❌ Invalid command, bro.")
(Note: Ensure your router in app/agents/router.py maps "health" to the PulseAgent!)

3️⃣ Restart & Run the Vitals ⚡
Restart the worker to load the new Medic logic: docker restart celery-worker

Run your new CLI command: hypercode pulse

Check the output file!

Hit that terminal, bro! Let’s see what the Swarm's heartbeat looks like! 💓🛠️
