import requests

API_URL = "http://localhost:8000/api/v1"

def run_test():
    # 1. Read Token
    try:
        with open("token.txt", "r") as f:
            token = f.read().strip()
    except FileNotFoundError:
        print("❌ token.txt not found. Run seed_data.py first.")
        return

    try:
        with open("project_id.txt", "r") as f:
            project_id = int(f.read().strip())
    except FileNotFoundError:
        print("❌ project_id.txt not found. Run seed_data.py first.")
        return
    except Exception:
        print("❌ project_id.txt is invalid. Run seed_data.py again.")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 2. Prepare Task Payload
    task_payload = {
        "title": "Translator Agent Test 01",
        "description": """
def process_user_cart(cart_items, user_tier):
    total = 0
    for item in cart_items:
        if item.in_stock:
            if user_tier == 'VIP':
                total += item.price * 0.8  # 20% discount
            else:
                total += item.price
    return total
""",
        "project_id": project_id,
        "status": "todo",
        "priority": "high",
        "type": "translate" # This triggers the TranslatorAgent
    }

    print(f"🚀 Firing Payload into HyperCode Core: {task_payload['title']}...")
    try:
        res = requests.post(f"{API_URL}/tasks/", json=task_payload, headers=headers)
        if res.status_code == 200:
            task = res.json()
            print(f"✅ Task Created Successfully! ID: {task['id']}")
            print(f"Title: {task['title']}")
            print("Check logs now: docker logs -f celery-worker")
        else:
            print(f"❌ Failed: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    run_test()
