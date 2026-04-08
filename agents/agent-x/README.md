# Agent X — Meta-Architect

**Agent X** is the autonomous evolutionary core of the HyperCode V2.0 ecosystem. It operates as the "Meta-Architect" with capabilities to scan, design, deploy, and evolve other agents dynamically.

## Architecture

- **Evolutionary Pipeline (`pipeline.py`)**: A multi-stage orchestration engine that scans agent health, identifies degradation, and triggers rebuilding processes.
- **LLM Agent Designer (`designer.py`)**: Utilizes Ollama (`qwen2.5-coder`) to generate Python code for new agent specs or specific agent code improvements.
- **Docker Ops (`docker_ops.py`)**: Directly interacts with the Docker daemon to deploy, build, and rollback container images autonomously.
- **AgentX Class (`main.py`)**: The central entry point integrating FastAPI, BackgroundTasks, and the pipeline lifecycle handlers.

## Key Features

1. **Agent Spawning**: Creates a new agent from scratch just from a text description.
2. **Agent Evolution**: Uses health metrics (success rate, error logs) to write code patches and safely blue-green deploy improved versions.
3. **Rollbacks**: If an evolution fails health checks, it automatically reverts to the last known-good Docker image.

## API Reference

### POST `/pipeline/run`
Run a full evolutionary pipeline cycle.
**Request**: `{"dry_run": true}`

### POST `/agents/spawn`
Generate and scaffold a brand new agent.
**Request**:
```json
{
  "description": "An agent that checks log files for errors",
  "auto_deploy": true
}
```

### POST `/agents/{name}/evolve`
Trigger an improvement for a specific agent.
**Request**: `{"dry_run": false}`

### GET `/health`
Standard readiness probe endpoint.

## Usage

Agent X is usually started via `docker-compose`. For local development:
```bash
export AGENT_PORT=8080
export OLLAMA_HOST=http://localhost:11434
python main.py
```

Run tests:
```bash
pytest test_agent_x.py
```
