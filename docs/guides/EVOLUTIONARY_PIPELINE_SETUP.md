# HyperCode Evolutionary Pipeline Setup Guide

This guide explains how the HyperCode Evolutionary Pipeline works and how to set it up. This pipeline allows agents (like the Coder or Architect) to programmatically request improvements to their own infrastructure, which are then executed autonomously by the DevOps agent.

## Overview

The pipeline consists of three main components:
1.  **Evolution Protocol**: A standardized data structure for improvement requests.
2.  **DevOps Listener**: A background process in the DevOps agent that watches for requests.
3.  **Deployment Engine**: A toolset that allows the DevOps agent to rebuild and redeploy containers.

### Workflow
1.  **Request**: An agent (e.g., Coder) identifies a need for a library update or configuration change.
2.  **Submission**: The agent submits an `ImprovementRequest` to the Redis Stream `events:improvement_requested`.
3.  **Execution**: The DevOps agent consumes the event, validates it, and executes the necessary Docker commands.
4.  **Deployment**: The target service is rebuilt (rolling update) with zero/minimal downtime.

## Prerequisites

- **Redis**: Required for the event bus.
- **Docker Socket**: The DevOps agent must have access to `/var/run/docker.sock`.
- **Shared Modules**: The `agents/shared` directory must be mounted or copied into all participating agents.

## Configuration

### 1. DevOps Agent (`agents/05-devops-engineer/`)
Ensure the DevOps agent has the following permissions in `docker-compose.yml`:

```yaml
  devops-engineer:
    # ...
    environment:
      - DOCKER_HOST=unix:///var/run/docker.sock
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
```

### 2. Requesting an Improvement (Python Example)

Any agent can trigger an evolution using the shared protocol:

```python
from agents.shared.protocols.evolution import ImprovementRequest, ImprovementType
import redis.asyncio as redis

# connect to redis
r = redis.from_url("redis://redis:6379")

# Create request
req = ImprovementRequest(
    agent_id="coder-agent",
    target_agent="test-agent",
    improvement_type=ImprovementType.PERFORMANCE,
    description="Optimizing build settings",
    payload={"action": "redeploy"}
)

# Submit
await r.xadd("events:improvement_requested", {"payload": req.model_dump_json()})
```

## Security Considerations

- **Scope**: The DevOps agent has full control over the Docker daemon. It should strictly validate `target_agent` against a whitelist.
- **Isolation**: Ensure the DevOps agent is isolated from sensitive production data if possible.
- **Rate Limiting**: The listener implements basic backoff, but rate limiting should be enforced at the submission level.

## Troubleshooting

- **Logs**: Check `docker logs devops-engineer` for "Processing improvement request" messages.
- **Redis**: Use `redis-cli xlen events:improvement_requested` to see if events are piling up.
- **Permissions**: If deployment fails with "permission denied", verify the Docker socket mount.
