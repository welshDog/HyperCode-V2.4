import subprocess
import json
import datetime
import requests

def run_command(command):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        return str(e)

def check_docker_containers():
    print("Checking Docker Containers...")
    raw_output = run_command("docker ps --format '{{.Names}}|{{.Status}}|{{.State}}|{{.Ports}}'")
    containers = []
    for line in raw_output.split('\n'):
        if not line: continue
        parts = line.split('|')
        if len(parts) >= 3:
            containers.append({
                "name": parts[0],
                "status": parts[1],
                "state": parts[2],
                "ports": parts[3] if len(parts) > 3 else ""
            })
    return containers

def check_endpoint(name, url):
    print(f"Checking {name} ({url})...")
    try:
        start = datetime.datetime.now()
        response = requests.get(url, timeout=5)
        latency = (datetime.datetime.now() - start).total_seconds() * 1000
        return {
            "name": name,
            "url": url,
            "status": response.status_code,
            "latency_ms": round(latency, 2),
            "healthy": response.status_code == 200
        }
    except Exception as e:
        return {
            "name": name,
            "url": url,
            "status": "ERROR",
            "latency_ms": 0,
            "healthy": False,
            "error": str(e)
        }

def check_disk_usage():
    print("Checking Docker Disk Usage...")
    return run_command("docker system df")

def check_logs_for_errors(container_name, lines=50):
    print(f"Checking logs for {container_name}...")
    logs = run_command(f"docker logs --tail {lines} {container_name}")
    error_count = logs.lower().count("error")
    warning_count = logs.lower().count("warn")
    return {
        "container": container_name,
        "error_count": error_count,
        "warning_count": warning_count,
        "recent_logs": logs[-500:] if len(logs) > 500 else logs
    }

def main():
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "infrastructure": {},
        "services": [],
        "resources": {},
        "logs": []
    }

    # 1. Infrastructure
    report["infrastructure"]["containers"] = check_docker_containers()
    
    # 2. Services
    endpoints = [
        ("HyperCode Core", "http://localhost:8000/health"),
        ("Orchestrator", "http://localhost:8081/health"),
        ("Dashboard", "http://localhost:3000"),
        ("Grafana", "http://localhost:3001"), # Port mapped
        # Add agent endpoints if accessible directly, usually they are internal
    ]
    
    for name, url in endpoints:
        report["services"].append(check_endpoint(name, url))

    # 3. Resources
    report["resources"]["docker_disk"] = check_disk_usage()
    
    # 4. Logs (Key containers)
    key_containers = ["hypercode-core", "crew-orchestrator", "tempo", "postgres"]
    # Map names to actual running container names if needed, usually docker ps gives names
    # Let's try to match them from the running list
    running_names = [c["name"] for c in report["infrastructure"]["containers"]]
    
    for target in key_containers:
        # Find partial match
        match = next((name for name in running_names if target in name), None)
        if match:
            report["logs"].append(check_logs_for_errors(match))

    # Output Report
    with open("health_check_results.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print("\nHealth Check Complete. Results saved to health_check_results.json")

if __name__ == "__main__":
    main()
