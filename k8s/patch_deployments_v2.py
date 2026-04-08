import subprocess
import json
import time
import sys

def run_kubectl(args):
    """Run kubectl command with retries"""
    max_retries = 3
    for i in range(max_retries):
        try:
            cmd = ["kubectl"] + args
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                print(f"Command failed (attempt {i+1}): {' '.join(cmd)}")
                print(result.stderr)
        except subprocess.TimeoutExpired:
            print(f"Command timed out (attempt {i+1}): {' '.join(cmd)}")
        except Exception as e:
            print(f"Error (attempt {i+1}): {e}")
        
        time.sleep(2)
    return None

def patch_resources(resource_type):
    print(f"Fetching {resource_type}s...")
    output = run_kubectl(["get", resource_type, "-n", "hypercode", "-o", "json"])
    if not output:
        print(f"Failed to list {resource_type}s")
        return

    try:
        resources = json.loads(output)
    except json.JSONDecodeError:
        print("Failed to decode JSON output")
        return

    for item in resources.get('items', []):
        name = item['metadata']['name']
        print(f"Patching {resource_type}: {name}")
        
        containers = item['spec']['template']['spec']['containers']
        patches = []
        for container in containers:
            patches.append({
                "name": container['name'],
                "imagePullPolicy": "IfNotPresent"
            })
            
        patch_spec = {
            "spec": {
                "template": {
                    "spec": {
                        "containers": patches
                    }
                }
            }
        }
        
        # Apply patch
        patch_json = json.dumps(patch_spec)
        result = run_kubectl(["patch", resource_type, name, "-n", "hypercode", "-p", patch_json])
        if result:
            print(f"Successfully patched {name}")
        else:
            print(f"Failed to patch {name}")

if __name__ == "__main__":
    print("Checking cluster connectivity...")
    if not run_kubectl(["cluster-info"]):
        print("Cluster seems unresponsive. Aborting.")
        sys.exit(1)
        
    patch_resources("deployment")
    patch_resources("statefulset")
    print("Patching complete.")
