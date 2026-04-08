# Option C: Stretch Enhancements Implementation Plan

## 1. Cost Optimization Module (Backend)
**Goal:** Track token usage and estimate costs per task.
- **Database:** Update `schema.prisma` to include a `TokenUsage` model linked to `Mission` (Task) IDs, storing `prompt_tokens`, `completion_tokens`, `model`, and `estimated_cost`.
- **Service Logic:** Modify `hypercode-core/app/services/llm.py` to:
    - Extract usage statistics from OpenAI API responses.
    - Calculate cost based on model pricing (e.g., GPT-4o rates).
    - Persist data to the new database table.
- **API:** Create a new endpoint `GET /api/v1/metrics/costs` to retrieve aggregated cost data.

## 2. Security Policy Engine (Coder Agent)
**Goal:** Granular control over what Docker images agents can pull/run.
- **Policy Definition:** Create `agents/coder/policy.yaml` (or Python class) defining a whitelist of allowed images (e.g., `python:3.9-slim`, `node:18-alpine`, `postgres:15`).
- **Enforcement:**
    - Modify `CoderAgent` in `agents/coder/main.py`.
    - Implement a `safe_call_tool` wrapper around the MCP client.
    - Intercept calls to `docker_run` or `docker_container_create`.
    - Block execution if the requested image is not in the whitelist.

## 3. CLI Plugin (Local Terminal Tool)
**Goal:** Interact with the swarm from the command line.
- **Setup:** Create a new `cli/` directory with a standalone Python application using `typer`.
- **Commands:**
    - `hypercode agents list`: View available agents and their status.
    - `hypercode run "task"`: Submit a new task to the swarm.
    - `hypercode cost`: View current session or total project costs.
- **Integration:** The CLI will communicate with the Core API via HTTP.

## Verification Plan
1.  **Cost:** Run a sample task and verify a new row appears in the `TokenUsage` table with a non-zero cost.
2.  **Security:** Attempt to deploy a `ubuntu:latest` container (not in whitelist) and verify the agent rejects the action with a "Policy Violation" error.
3.  **CLI:** Execute `python cli/main.py agents list` and confirm it displays the registered Coder Agent.
