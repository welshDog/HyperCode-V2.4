"""
HyperCode Deployment Tool
Provides Docker control capabilities for the DevOps agent.
"""
import subprocess
import logging
from typing import Dict, Any

logger = logging.getLogger("deployer")

class Deployer:
    """Handles container management and deployment tasks"""
    
    @staticmethod
    def list_containers() -> str:
        """Returns list of running containers"""
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "table {{.ID}}\t{{.Names}}\t{{.Status}}"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            return f"Error listing containers: {e.stderr}"

    @staticmethod
    def deploy_service(service_name: str) -> Dict[str, Any]:
        """
        Rebuilds and restarts a specific service.
        """
        logger.info(f"Initiating deployment for {service_name}")
        
        try:
            # 1. Build
            logger.info("Building...")
            # We assume docker compose v2 is available as a plugin or standalone
            # But inside the container we only installed docker.io which gives us `docker` cli.
            # Docker Compose v2 is usually `docker compose`, but v1 was `docker-compose`.
            # In standard docker.io package on debian, compose plugin might not be included.
            
            # Let's try to detect if we should use `docker-compose` or `docker compose`
            # For now, let's assume we need to install the plugin or use a different command.
            # Since the error was "docker: 'compose' is not a docker command", we lack the plugin.
            
            # However, installing the plugin inside the container adds complexity.
            # A simpler approach for self-hosted agents might be just restarting the container
            # if the image is built elsewhere. But here we are building it.
            
            # WORKAROUND: If we can't build, we can at least try to restart.
            # But the requirement is to BUILD.
            
            # Let's try to use the legacy `docker-compose` if available, or just fail for now.
            # But we can fix the command to standard `docker` commands if compose is missing.
            # `docker build` + `docker stop` + `docker rm` + `docker run`? Too complex due to networking.
            
            # Better fix: Install docker-compose-plugin in the Dockerfile.
            
            build_res = subprocess.run(
                ["docker", "compose", "build", service_name],
                capture_output=True,
                text=True,
                check=True
            )
            
            # 2. Up (Rolling update)
            logger.info("Restarting...")
            up_res = subprocess.run(
                ["docker", "compose", "up", "-d", "--no-deps", service_name],
                capture_output=True,
                text=True,
                check=True
            )
            
            return {
                "status": "success",
                "message": f"Deployed {service_name}",
                "build_log": build_res.stdout,
                "deploy_log": up_res.stdout
            }
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Deployment failed: {e.stderr}")
            return {
                "status": "error",
                "message": f"Deployment failed: {e.stderr}",
                "exit_code": e.returncode
            }
            
    @staticmethod
    def get_service_logs(service_name: str, lines: int = 50) -> str:
        """Fetch recent logs for validation"""
        try:
            result = subprocess.run(
                ["docker", "logs", "--tail", str(lines), service_name],
                capture_output=True,
                text=True
            )
            return result.stdout + result.stderr
        except Exception as e:
            return f"Error fetching logs: {str(e)}"
