import requests
import sys
import time

CORE_URL = "http://localhost:8000"
DASHBOARD_URL = "http://hypercode-dashboard:3000"

def check_url(url, name):
    print(f"Checking {name} at {url}...", flush=True)
    try:
        start = time.time()
        response = requests.get(url, timeout=5, verify=False)
        duration = time.time() - start
        if response.status_code == 200:
            print(f"[PASS] {name} is reachable ({duration:.3f}s)", flush=True)
            return True
        else:
            print(f"[FAIL] {name} returned {response.status_code}", flush=True)
            return False
    except Exception as e:
        print(f"[FAIL] {name} unreachable: {e}", flush=True)
        return False

def main():
    print("Starting HyperCode Internal Smoke Tests...", flush=True)
    
    # Core API
    core_ok = check_url(f"{CORE_URL}/health", "HyperCode Core Health")
    
    # Dashboard
    dash_ok = check_url(f"{DASHBOARD_URL}", "HyperCode Dashboard")

    if core_ok and dash_ok:
        print("\n✅ SMOKE TESTS PASSED", flush=True)
        sys.exit(0)
    else:
        print("\n❌ SMOKE TESTS FAILED", flush=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
