"""
Smart Docker Auto-Deploy
Watches files -> Rebuilds images -> Redeploys containers
Perfect for dev workflow
"""

import os
import sys
import time
import subprocess
import json
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import docker

client = docker.from_env()

class DockerAutoDeployer(FileSystemEventHandler):
    """Watch files and auto-rebuild/redeploy"""
    
    def __init__(self, watch_dir, dockerfile, image_name, container_name, ports, volumes):
        self.watch_dir = watch_dir
        self.dockerfile = dockerfile
        self.image_name = image_name
        self.container_name = container_name
        self.ports = ports or {}
        self.volumes = volumes or {}
        self.cooldown = 0
    
    def on_modified(self, event):
        """Trigger rebuild on file change"""
        if event.is_directory or ".git" in event.src_path or "__pycache__" in event.src_path:
            return
        
        # Cooldown to prevent multiple rebuilds
        if time.time() - self.cooldown < 3:
            return
        
        self.cooldown = time.time()
        print(f"\nFILE CHANGED: {event.src_path}")
        self.rebuild_and_deploy()
    
    def rebuild_and_deploy(self):
        """Rebuild Docker image and redeploy"""
        print(f"\n{'='*80}")
        print(f"REBUILDING: {self.image_name}")
        print(f"{'='*80}")
        
        # Build image
        try:
            print(f"[BUILD] Building {self.image_name}...")
            output = subprocess.run(
                ["docker", "build", "-f", self.dockerfile, "-t", self.image_name, "."],
                cwd=self.watch_dir,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if output.returncode == 0:
                print(f"[BUILD] SUCCESS - Image built")
            else:
                print(f"[BUILD] FAILED - {output.stderr}")
                return
        except Exception as e:
            print(f"[BUILD] ERROR - {str(e)}")
            return
        
        # Stop old container
        try:
            container = client.containers.get(self.container_name)
            if container.status == "running":
                print(f"[DEPLOY] Stopping old container...")
                container.stop(timeout=5)
                print(f"[DEPLOY] Stopped")
        except docker.errors.NotFound:
            pass
        except Exception as e:
            print(f"[DEPLOY] Stop error - {str(e)}")
        
        # Remove old container
        try:
            container = client.containers.get(self.container_name)
            container.remove()
            print(f"[DEPLOY] Removed old container")
        except docker.errors.NotFound:
            pass
        except Exception as e:
            print(f"[DEPLOY] Remove error - {str(e)}")
        
        # Run new container
        try:
            print(f"[DEPLOY] Starting new container...")
            container = client.containers.run(
                self.image_name,
                name=self.container_name,
                ports=self.ports,
                volumes=self.volumes,
                detach=True,
                restart_policy={"Name": "unless-stopped"}
            )
            print(f"[DEPLOY] SUCCESS - Container running: {container.id[:12]}")
            
            # Wait for health
            print(f"[MONITOR] Waiting for container to be healthy...")
            for _ in range(30):
                container.reload()
                status = container.status
                health = container.attrs.get("State", {}).get("Health", {}).get("Status", "none")
                print(f"  Status: {status}, Health: {health}")
                
                if status == "running" and (health == "healthy" or health == "none"):
                    print(f"[MONITOR] Container is ready!")
                    break
                time.sleep(1)
        except Exception as e:
            print(f"[DEPLOY] RUN ERROR - {str(e)}")

def watch_and_deploy(config_file: str):
    """Load config and start watcher"""
    try:
        with open(config_file, "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Config file not found: {config_file}")
        return
    
    watch_dir = config.get("watch_dir", ".")
    dockerfile = config.get("dockerfile", "Dockerfile")
    image_name = config.get("image_name", "app:dev")
    container_name = config.get("container_name", "app-dev")
    ports = config.get("ports", {})
    volumes = config.get("volumes", {})
    
    print(f"\n{'='*80}")
    print(f"HYPERFOCUS AUTO-DEPLOY")
    print(f"{'='*80}")
    print(f"Watching: {watch_dir}")
    print(f"Dockerfile: {dockerfile}")
    print(f"Image: {image_name}")
    print(f"Container: {container_name}")
    print(f"\nWatching for changes... (Press Ctrl+C to stop)")
    print(f"{'='*80}\n")
    
    event_handler = DockerAutoDeployer(
        watch_dir=watch_dir,
        dockerfile=dockerfile,
        image_name=image_name,
        container_name=container_name,
        ports=ports,
        volumes=volumes
    )
    
    observer = Observer()
    observer.schedule(event_handler, watch_dir, recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping watcher...")
        observer.stop()
    observer.join()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Example config
        example_config = {
            "watch_dir": ".",
            "dockerfile": "Dockerfile",
            "image_name": "myapp:dev",
            "container_name": "myapp-dev",
            "ports": {"8000/tcp": 8000},
            "volumes": {"/app": {"bind": "/app", "mode": "rw"}}
        }
        
        config_file = "deploy.json"
        with open(config_file, "w") as f:
            json.dump(example_config, f, indent=2)
        
        print(f"Created example config: {config_file}")
        print("Edit it and run: python auto_deploy.py deploy.json")
    else:
        watch_and_deploy(sys.argv[1])
