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
            print("👀 Keep an eye on the docs/outputs folder for the magic!")
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
            print(f"👀 Check docs/outputs/translation_{task_id}.md for the diagnosis!")
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
            print("👀 Go grab a coffee. The brief will drop in docs/outputs soon!")
        else:
            print(f"⚠️ Tripped up: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"🛑 Backend offline? Error: {e}")

def create_task(description, task_type="general"):
    """Generic task creator."""
    token = get_token()
    if not token:
        print("❌ Missing auth token! Please run seed_data.py or ensure token.txt exists.")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    print(f"📡 Dispatching '{task_type}' task: {description}")
    
    payload = {
        "title": f"CLI Task: {description[:20]}...",
        "description": description,
        "priority": "normal",
        "type": task_type,
        "project_id": 1
    }

    try:
        response = requests.post(API_URL, json=payload, headers=headers)
        if response.status_code == 200:
            task_data = response.json()
            print(f"✅ Task queued! ID: {task_data['id']}")
            print("👀 Monitor the dashboard or logs for updates.")
        else:
            print(f"❌ API Error: {response.text}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

def main():
    if len(sys.argv) < 3:
        print("Usage: python hypercode.py <translate|research|build> <file_path|topic>")
        return

    command = sys.argv[1]

    if command == "translate" and len(sys.argv) == 3:
        translate_file(sys.argv[2])
    elif command == "pulse":
        check_pulse()
    elif command == "research" and len(sys.argv) >= 3:
        # Join all arguments after "research" into a single string
        topic = " ".join(sys.argv[2:])
        research_topic(topic)
    elif command == "task" or command == "build":
        description = sys.argv[2]
        create_task(description, "build")
    else:
        print("❌ Invalid command, bro.")
