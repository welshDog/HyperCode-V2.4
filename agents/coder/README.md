# Coder Agent

The **Coder Agent** is a specialized module responsible for analyzing, generating, and deploying code within the HyperCode V2.0 ecosystem. It leverages local Large Language Models (LLMs) via Ollama and interfaces directly with the system to verify health and deploy changes.

## Architecture

- **Agent Class**: Encapsulates configuration and application lifecycle. Uses Dependency Injection for API clients and Redis connections.
- **FastAPI Router**: Exposes endpoints for executing code-related tasks.
- **BaseAgent Compatibility**: Fully compatible with the `BaseAgent` standard format using `TaskRequest` and `TaskResponse` schema definitions.

## Key Features

1. **State Management**: Asynchronous state handlers (`startup`/`shutdown`) for safe resource initialization (Redis, HTTP clients).
2. **Error Handling**: Structured JSON responses for predictable error propagation.
3. **Inter-Agent Messaging**: Uses `httpx.AsyncClient` to securely forward requests to Ollama and system APIs.
4. **Code Generation**: Integrates with `qwen2.5-coder` (or any compatible model) to write code autonomously.

## API Reference

### POST `/execute`
Execute a coding task.

**Request Body (`TaskRequest`)**:
```json
{
  "id": "task-uuid-123",
  "task": "Build a React component",
  "context": {}
}
```

**Response (`TaskResponse`)**:
```json
{
  "task_id": "task-uuid-123",
  "agent": "coder-agent",
  "status": "completed",
  "result": {
    "status": "completed",
    "code": "export const Component = () => <div/>"
  }
}
```

### GET `/health`
Check agent health. Returns HTTP 200 with basic status details.

## Usage

Start the agent directly using Uvicorn:
```bash
export AGENT_NAME=coder-agent
export AGENT_PORT=8002
python main.py
```

Run tests:
```bash
pytest test_coder.py
```
