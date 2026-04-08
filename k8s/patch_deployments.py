import subprocess
import json

def run_command(command):
    try:
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {command}")
        print(e.stderr)
        return None

def patch_resources(resource_type):
    print(f"Fetching {resource_type}s...")
    cmd = f"kubectl get {resource_type} -n hypercode -o json"
    output = run_command(cmd)
    if not output:
        return

    resources = json.loads(output)
    for item in resources.get('items', []):
        name = item['metadata']['name']
        print(f"Patching {resource_type}: {name}")
        
        # Patch command using strategic merge patch
        # We need to know container name, but strategic merge patch can merge by name if provided, 
        # or we can just iterate containers in python and construct the patch.
        
        containers = item['spec']['template']['spec']['containers']
        patches = []
        for container in containers:
            patches.append({
                "name": container['name'],
                "imagePullPolicy": "IfNotPresent"
            })
            
        patch_json = {
            "spec": {
                "template": {
                    "spec": {
                        "containers": patches
                    }
                }
            }
        }
        
        json.dumps(patch_json).replace('"', '\\"') # Escape quotes for shell if needed, but subprocess handles list args better.
        
        # Using subprocess with list args avoids shell escaping hell
        cmd_list = [
            "kubectl", "patch", resource_type, name, "-n", "hypercode",
            "-p", json.dumps(patch_json)
        ]
        
        subprocess.run(cmd_list, check=False) # Don't exit on error

print("Starting patching process...")
patch_resources("deployment")
patch_resources("statefulset")
print("Patching complete.")
