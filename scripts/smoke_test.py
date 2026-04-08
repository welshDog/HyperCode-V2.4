import requests
import sys
import time

CORE_URL = "http://localhost/api"
TERMINAL_URL = "http://localhost"
EDITOR_URL = "http://localhost:5173"

def check_url(url, name):
    try:
        start = time.time()
        # Disable SSL verification for self-signed certs
        response = requests.get(url, timeout=5, verify=False)
        duration = time.time() - start
        if response.status_code == 200:
            print(f"[PASS] {name} is reachable ({duration:.3f}s)")
            return True
        else:
            print(f"[FAIL] {name} returned {response.status_code}")
            return False
    except Exception as e:
        print(f"[FAIL] {name} unreachable: {e}")
        return False

def main():
    print("Starting HyperCode Production Smoke Tests...")
    
    # 1. Core API Health
    core_ok = check_url(f"{CORE_URL}/health", "HyperCode Core Health")
    
    # 2. Core Metrics
    metrics_ok = check_url(f"{CORE_URL}/metrics", "HyperCode Metrics")
    
    # 3. Terminal Frontend
    term_ok = check_url(f"{TERMINAL_URL}/api/health", "Broski Terminal API")
    
    # 4. Editor Frontend (Just check root)
    try:
        # Disable SSL verification for self-signed certs
        requests.get(EDITOR_URL, timeout=5, verify=False)
        print("[PASS] HyperFlow Editor is reachable")
        editor_ok = True
    except:
        print("[FAIL] HyperFlow Editor unreachable")
        editor_ok = False

    if core_ok and metrics_ok and term_ok and editor_ok:
        print("\n✅ SMOKE TESTS PASSED: System is GO for launch.")
        sys.exit(0)
    else:
        print("\n❌ SMOKE TESTS FAILED: Fix issues before launch.")
        sys.exit(1)

if __name__ == "__main__":
    main()
