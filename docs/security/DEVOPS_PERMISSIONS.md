# DevOps Permissions & Security Policy

## Overview
The DevOps Agent (`agents/05-devops-engineer`) is a critical component of the HyperCode Evolutionary Pipeline. It possesses elevated privileges to manage the container lifecycle. This document outlines the security boundaries and permission model.

## Privileges

### Docker Socket Access
The DevOps agent is granted access to `/var/run/docker.sock`.
- **Capability**: Can start, stop, build, and remove any container on the host system.
- **Risk**: High. Compromise of this agent is equivalent to root access on the host.
- **Mitigation**:
    - The agent runs as a non-root user inside the container (where possible, though Docker socket access usually requires root or `docker` group).
    - Access is strictly limited to the `devops-engineer` service in `docker-compose.yml`.

### Deployment Scope
The agent is authorized to deploy services defined in the project's `docker-compose.yml`.
- **Allowed Actions**: `build`, `up`, `logs`.
- **Prohibited Actions**: `system prune` (unless explicitly requested), modifying host files outside of the workspace.

## Best Practices

1.  **Request Validation**:
    The agent must validate `ImprovementRequest` payloads. It should not execute arbitrary shell commands passed in the payload unless they are part of a strictly defined build process.

2.  **Least Privilege**:
    Only the DevOps agent should have the Docker socket mounted. Other agents (Coder, Architect) interact *only* via the Redis event bus and do not have direct Docker access.

3.  **Audit Trail**:
    All actions taken by the DevOps agent are logged to `events:deployment:success` or `events:deployment:failure` in Redis, creating an immutable audit trail of infrastructure changes.

## Incident Response

If the DevOps agent behaves abnormally:
1.  **Kill Switch**: Immediately stop the container: `docker stop devops-engineer`.
2.  **Revoke Access**: Remove the `/var/run/docker.sock` volume from `docker-compose.yml` and redeploy.
3.  **Investigate**: Analyze Redis streams for malicious `ImprovementRequest` payloads.
