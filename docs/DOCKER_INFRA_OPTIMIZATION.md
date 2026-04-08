# Docker Infrastructure Audit & Optimization

## What Changed

### Compose networking

- `docker-compose.yml` no longer requires pre-created external networks by default.
- If you need to join existing shared networks, use `docker-compose.external-net.yml` as an overlay.

Examples:

```bash
docker compose -f docker-compose.yml up -d
```

```bash
docker compose -f docker-compose.yml -f docker-compose.external-net.yml up -d
```

To match existing network names in your environment:

```bash
HYPERCODE_PUBLIC_NET_NAME=hypercode_public_net \
HYPERCODE_AGENTS_NET_NAME=hypercode-v24_hypercode-net \
docker compose -f docker-compose.yml -f docker-compose.external-net.yml up -d
```

### Monitoring stack

- `docker-compose.monitoring.yml` is now self-contained (declares `prometheus-data` and `grafana-data`) and does not require an external network to exist.

### Dev stack

- `docker-compose.dev.yml` now targets the v2.4 backend layout (`./backend`) and uses existing Dockerfiles.
- Removed debug port mappings (no `debugpy` listener by default).
- Dev passwords use safe defaults to keep `docker compose config` functional.

### Dockerfiles (base image and supply-chain hardening)

- `Dockerfile.production` and `Dockerfile.builder` now use `python:3.11-slim-bookworm` instead of an invalid `python:3.14-slim`.
- Removed `curl | sh` installation patterns for Trivy and Docker inside those images (scanning is handled in CI).
- `quantum-compiler/Dockerfile` now pins Alpine instead of using `alpine:latest`.
- `hyper-mission-system` Dockerfiles updated to Node 20 and switched to `npm ci` where applicable.
- `agents/business/project-strategist` Dockerfile updated to Python 3.11 and runs as a non-root user.
- `backend/Dockerfile` runtime now uses `libpq5` instead of `libpq-dev`.

## CI/CD Improvements

### GitHub Actions version fixes

- Updated workflows that referenced non-existent action versions (for example `actions/checkout@v6`) to supported releases.

### Docker build improvements

- Docker build workflow now builds:
  - Core API image from `./backend`
  - Dashboard image from `./agents/dashboard`
- Enables Buildx cache (`type=gha`) for faster incremental builds.

### Automated rollback (Kubernetes)

- Added `scripts/deployment/k8s_deploy_with_rollback.sh`:
  - Applies manifests
  - Waits for rollout completion
  - Rolls back on failure
- `ci-cd.yml` deploy jobs now use this script (expects `KUBECONFIG_B64` secret).

## Monitoring & Health

- Compose stacks already expose Prometheus/Grafana/cAdvisor to localhost in the primary stack, reducing remote attack surface by default.
- Existing service-level `healthcheck` configuration remains the primary readiness gate for orchestration.

## Follow-ups (Recommended)

- Replace direct Docker socket mounts in agent/ops containers with a socket proxy pattern (implemented in the v2.4 compose files).
  - Only `docker-socket-proxy` mounts `/var/run/docker.sock` (read-only) and exposes a narrow HTTP API inside the compose network.
  - Containers that need Docker access use `DOCKER_HOST=tcp://docker-socket-proxy:2375` and do not mount the socket.

- Docker build API exposure:
  - `docker-socket-proxy` now runs with `BUILD=0` to prevent runtime image builds from healer/coder/throttle paths.
  - A separate `docker-socket-proxy-build` exists for opt-in workflows that require building images at runtime (for example Agent X build/deploy operations and ops-only pruning).

- Replace any remaining direct Docker socket mounts with a socket proxy (read-only by default, write access only behind an explicit ops profile).
- Add image digest pinning for production deployments once tested tags are established.
- Add Dockerfile linting (hadolint) and SBOM generation in CI if you want stricter supply-chain posture.
