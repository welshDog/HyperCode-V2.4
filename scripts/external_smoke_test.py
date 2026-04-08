import requests

def check_url(url, name):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(f"[PASS] {name} is reachable: {response.status_code}")
            return True
        else:
            print(f"[FAIL] {name} returned {response.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] {name} unreachable: {e}")
        return False

print("Checking External Access...")
check_url("http://localhost:8000/health", "HyperCode Core (External)")
check_url("http://localhost:8088", "HyperCode Dashboard (External)")
