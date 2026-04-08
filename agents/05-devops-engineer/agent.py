"""
DevOps Engineer Agent
Specializes in CI/CD, infrastructure, and deployment automation.
Handles the Evolutionary Pipeline for self-updating agents.
"""
import sys
import asyncio
import json
import logging
from typing import Dict, Any

# Add /app to sys.path so we can import 'agents.shared' if needed
sys.path.append('/app')

# IMPORTANT: Also add the root of the shared modules if needed, 
# but since the structure is /app/agents/shared, importing 'agents.shared.x' requires '/app' in path.
# However, inside the container, we see 'agents' folder in /app.
# So 'import agents.shared...' should work if /app is in sys.path.

from base_agent import BaseAgent, AgentConfig

# Try importing shared modules, handle missing dependencies gracefully
try:
    # We explicitly import the submodule we need
    # Since /app is in path, and /app/agents/shared exists
    # We should be able to import 'agents.shared.tools.deployer'
    
    # Debug: Check if we can import just 'agents'
    import agents
    logging.getLogger("devops-agent").info(f"Agents package: {agents}")
    
    # Inside the container, 'agents' is a top-level package.
    # 'shared' is inside 'agents'.
    # So 'agents.shared' should be valid if 'agents' is a package (has __init__.py).
    
    # Check if agents has __init__.py
    import os
    if not os.path.exists("/app/agents/__init__.py"):
        # If it doesn't exist, create it dynamically to make it a package
        # However, 'agents' is a NamespacePackage because it lacks __init__.py
        # Namespace packages allow imports of subpackages.
        pass

    from agents.shared.tools.deployer import Deployer
    from agents.shared.protocols.evolution import ImprovementRequest
    SHARED_MODULES_AVAILABLE = True
except ImportError as e:
    # Log the specific error to help debugging
    logging.getLogger("devops-agent").warning(f"Shared modules import failed: {e}")
    # Fallback for local testing or if copy failed
    SHARED_MODULES_AVAILABLE = False

logger = logging.getLogger("devops-agent")

class DevOpsEngineer(BaseAgent):
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.evolution_stream_key = "events:improvement_requested"
        self.deployment_history_key = "history:deployments"
        
        # Register Deployment Tools if available
        if SHARED_MODULES_AVAILABLE:
            self.register_tool(Deployer.list_containers)
            self.register_tool(Deployer.deploy_service)
            self.register_tool(Deployer.get_service_logs)
        else:
            logger.warning("Shared modules missing: Evolution Protocol disabled")

    async def initialize(self):
        """Start the background listener for evolution events"""
        await super().initialize()
        if SHARED_MODULES_AVAILABLE:
            asyncio.create_task(self.listen_for_improvements())
            logger.info("DevOps Agent initialized with Evolution Listener")
        else:
            logger.info("DevOps Agent initialized (Limited Mode)")

    async def listen_for_improvements(self):
        """
        Consumes the improvement request stream and triggers deployments.
        Implements exponential backoff for resilience.
        """
        last_id = "$" # Listen for new messages only
        
        while True:
            try:
                # Blocking read from Redis Stream
                streams = await self.redis.xread(
                    {self.evolution_stream_key: last_id}, 
                    count=1, 
                    block=5000
                )
                
                if not streams:
                    continue
                    
                for stream_name, messages in streams:
                    for message_id, data in messages:
                        last_id = message_id
                        await self.process_improvement_request(data)
                        
            except Exception as e:
                logger.error(f"Error in evolution listener: {e}")
                await asyncio.sleep(5) # Backoff on error

    async def process_improvement_request(self, data: Dict[str, Any]):
        """
        Orchestrates the deployment pipeline for a request.
        """
        try:
            payload_json = data.get('payload', '{}')
            req_data = json.loads(payload_json)
            request = ImprovementRequest(**req_data)
            
            logger.info(f"Processing improvement request: {request.id} for {request.target_agent}")
            
            # 1. Update Status -> DEPLOYING
            # (In a real system, we'd update a status KV store here)
            
            # 2. Trigger Deployment
            result = Deployer.deploy_service(request.target_agent)
            
            # 3. Handle Result
            if result['status'] == 'success':
                logger.info(f"Deployment SUCCESS: {request.target_agent}")
                # Emit Success Event
                await self.redis.publish("events:deployment:success", json.dumps({
                    "request_id": request.id,
                    "agent": request.target_agent,
                    "logs": result.get('build_log')
                }))
            else:
                logger.error(f"Deployment FAILED: {result['message']}")
                # Emit Failure Event
                await self.redis.publish("events:deployment:failure", json.dumps({
                    "request_id": request.id,
                    "error": result['message']
                }))
                
        except Exception as e:
            logger.error(f"Failed to process improvement: {e}")

    def build_system_prompt(self) -> str:
        base_prompt = super().build_system_prompt()
        return f"""{base_prompt}

**Your Specialization: DevOps & Infrastructure**

TECH STACK:
- Docker & Docker Compose
- Kubernetes (K8s)
- GitHub Actions
- Terraform
- Prometheus + Grafana
- nginx / Traefik

RESPONSIBILITIES:
- Design CI/CD pipelines
- Create Dockerfiles and compose files
- Write Kubernetes manifests
- Implement infrastructure as code
- Set up monitoring and alerting
- Manage deployments and rollbacks
- **Execute Evolutionary Improvements** for other agents

DOCKERFILE BEST PRACTICES:
- Multi-stage builds for size optimization
- Layer caching (order least→most changing)
- Use specific image tags, not 'latest'
- Combine RUN commands to reduce layers
- Use .dockerignore
- Non-root user for security
- Health checks included

KUBERNETES:
- Use Deployments for stateless apps
- StatefulSets for databases
- ConfigMaps for configuration
- Secrets for sensitive data
- Horizontal Pod Autoscaling (HPA)
- Resource limits and requests

CI/CD PIPELINE:
1. Lint & Format (pre-commit)
2. Unit Tests
3. Build Docker image
4. Integration Tests
5. Security scan
6. Push to registry
7. Deploy to staging
8. E2E tests
9. Deploy to production

MONITORING:
- Application metrics (Prometheus)
- Logs aggregation (ELK/Loki)
- Distributed tracing (Jaeger)
- Uptime monitoring
- Alert on SLI violations

DEPLOYMENT STRATEGIES:
- Blue-Green for zero downtime
- Canary for gradual rollout
- Rolling updates for K8s
- Feature flags for testing
"""

if __name__ == "__main__":
    config = AgentConfig()
    agent = DevOpsEngineer(config)
    agent.run()
