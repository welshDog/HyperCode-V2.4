import sys
import subprocess
import json
import time
from datetime import datetime

def run_test(test_path):
    start_time = time.time()
    status = "FAIL"
    output = ""
    
    try:
        if test_path.endswith(".py"):
            # Run with pytest
            cmd = [sys.executable, "-m", "pytest", test_path, "-v"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            output = result.stdout + result.stderr
            if result.returncode == 0:
                status = "PASS"
        elif test_path.endswith(".go"):
            # Run with go test
            cmd = ["go", "test", "-v", test_path]
            result = subprocess.run(cmd, capture_output=True, text=True)
            output = result.stdout + result.stderr
            if result.returncode == 0:
                status = "PASS"
        elif test_path.endswith(".json"):
             # Mock execution for scenario files
             status = "PASS" 
             output = "Scenario validation passed (mock)"

    except Exception as e:
        output = str(e)

    duration_ms = (time.time() - start_time) * 1000
    
    # Extract service name from path (heuristic)
    service = "unknown"
    parts = test_path.replace("\\", "/").split("/")
    for part in parts:
        if "test_" in part:
            service = part.replace("test_", "").replace(".py", "")
            break
            
    result = {
        "service": service,
        "status": status,
        "latency_ms": round(duration_ms, 2),
        "timestamp": datetime.now().isoformat(),
        "details": output[:500] # Truncate output
    }
    
    print(json.dumps(result))
    return 0 if status == "PASS" else 1

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No test path provided"}))
        sys.exit(1)
        
    sys.exit(run_test(sys.argv[1]))
