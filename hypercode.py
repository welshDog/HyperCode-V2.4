import sys
import os
import requests

API_URL = "http://localhost:8000/api/v1/tasks/"

def get_token():
    """Retrieves the auth token from token.txt."""
    token_path = "token.txt"
    if not os.path.exists(token_path):
        return None
    with open(token_path, "r") as f:
        return f.read().strip()

def translate_file(filepath):
    """Reads a local file and sends it to the Translator Agent."""
    if not os.path.exists(filepath):
        print(f"❌ Bro, I can't find that file: {filepath}")
        return

    print(f"👁️ Scanning {filepath}...")
    with open(filepath, "r", encoding="utf-8") as f:
        code_content = f.read()

    token = get_token()
    if not token:
        print("❌ Missing auth token! Please run seed_data.py or ensure token.txt exists.")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    print("📡 Beaming code to the Cognitive Swarm...")
    
    # Corrected payload to match TaskCreate schema
    payload = {
        "title": f"CLI Translation: {os.path.basename(filepath)}",
        "description": code_content,
        "priority": "high",
        "type": "translate",
        "project_id": 1 # Defaulting to project 1
    }

    try:
        response = requests.post(API_URL, json=payload, headers=headers)
        if response.status_code == 200:
            task_data = response.json()
            task_id = task_data.get("id", "UNKNOWN")
            print(f"✅ BOOM! Task {task_id} queued.")
            print(f"👀 Output will appear in docs/outputs/translate_{task_id}.md")
        else:
            print(f"⚠️ Something tripped up: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"🛑 Backend offline? Is Docker running, mate? Error: {e}")

def check_pulse():
    print("🏥 Pinging the Pulse Agent (The Medic)...")
    
    token = get_token()
    if not token:
        print("❌ Missing auth token! Please run seed_data.py or ensure token.txt exists.")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "title": "System Health Check",
        "description": "Check swarm vitals",
        "priority": "high",
        "type": "health", # Routes to PulseAgent!
        "project_id": 1
    }

    try:
        response = requests.post(API_URL, json=payload, headers=headers) 
        if response.status_code == 200:
            task_id = response.json().get("id", "UNKNOWN")
            print(f"✅ Pulse check queued! Task ID: {task_id}")
            print(f"👀 Output will appear in docs/outputs/health_{task_id}.md")
        else:
            print(f"⚠️ Tripped up: {response.text}")
    except Exception as e:
        print(f"🛑 Backend offline? Error: {e}")

def research_topic(topic):
    print(f"📚 Waking up The Archivist to research: '{topic}'...")
    
    token = get_token()
    if not token:
        print("❌ Missing auth token! Please run seed_data.py or ensure token.txt exists.")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    payload = {
        "title": f"Research: {topic}",
        "description": topic,
        "priority": "normal",
        "type": "research", # Routes to the Research Agent!
        "project_id": 1
    }

    try:
        response = requests.post(API_URL, json=payload, headers=headers)
        if response.status_code == 200:
            task_id = response.json().get("id", "UNKNOWN")
            print(f"✅ Research queued! Task ID: {task_id}")
            print(f"👀 Output will appear in docs/outputs/research_{task_id}.md")
        else:
            print(f"⚠️ Tripped up: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"🛑 Backend offline? Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("🚀 HYPERCODE CLI v1.2")
        print("👉 Usage:")
        print("   python hypercode.py translate <file.py>")
        print("   python hypercode.py pulse")
        print("   python hypercode.py research \"Your wild topic here\"")
        sys.exit(1)

    command = sys.argv[1]

    if command == "translate" and len(sys.argv) == 3:
        translate_file(sys.argv[2])
    elif command == "pulse":
        check_pulse()
    elif command == "research" and len(sys.argv) >= 3:
        # Join all arguments after "research" into a single string
        topic = " ".join(sys.argv[2:])
        research_topic(topic)
    else:
        print("❌ Invalid command, bro.")
