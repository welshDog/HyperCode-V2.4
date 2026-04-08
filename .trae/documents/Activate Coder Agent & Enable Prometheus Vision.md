# Phase 2 & 3: "The Brain" Implementation Plan 🧠

We are merging the infrastructure (Prometheus) with the intelligence (Coder Agent) to create a closed-loop system.

## 1. Infrastructure Update (Docker Compose)
We will formally add the `coder-agent` to the main `docker-compose.yml`.
- **Service**: `coder-agent`
- **Network**: `hypernet` (Shared with Prometheus)
- **Environment**: `CORE_URL=http://hypercode-core:8000`, `PROMETHEUS_URL=http://prometheus:9090`
- **Resources**: Limited to 0.5 CPU / 512MB RAM to start.

## 2. Agent Brain Upgrade (Python)
We will upgrade the `coder-agent` from a "dumb" script to a metric-aware system.
- **Dependencies**: Add `prometheus-api-client` to `agents/coder/requirements.txt`.
- **Logic (`agents/coder/main.py`)**:
    - **Connect**: Initialize connection to Prometheus.
    - **Analyze**: Add a new capability `analyze_metrics` that queries for high CPU/Memory.
    - **React**: (Placeholder) Logic to suggest optimizations when metrics are bad.

## 3. Verification
- We will rebuild the `coder-agent` container.
- We will verify the agent registers with `hypercode-core`.
- We will verify the agent can ping Prometheus.

**Why this works**: This creates the "Option D" architecture where the Agent is a microservice that "sees" the infrastructure state.
