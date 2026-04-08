# 🧠 Cognitive Uplink Guide

## Overview
The **Cognitive Uplink** is the **Primary Neural Interface** for the HyperCode agent swarm. It enables **Bidirectional Communication** between human operators (Captain) and the autonomous AI agents (Crew).

## Capabilities

*   **Task Delegation**: Assign complex tasks to specialized agents (e.g., "Research...", "Build...", "Analyze...").
*   **Real-time Feedback**: Visualize the AI's "thought process" (Logic, Creative, Memory cores) as it executes commands.
*   **Contextual Memory**: Agents recall previous interactions and build upon established context.

## How It Works

1.  **Input**: You type a directive into the Dashboard terminal.
2.  **Routing**: The **Agent Router** analyzes your intent and dispatches the task to the most suitable agent.
3.  **Execution**: The agent performs the task, potentially consulting the **Brain** (Perplexity AI) or accessing external tools.
4.  **Response**: The agent streams its findings back to the Uplink interface in real-time.

## Usage

### Dashboard Interface
Navigate to the **Cognitive Uplink** tab in the Mission Control Dashboard (`http://localhost:8088`).

### CLI Commands
You can also interact via the CLI:

```bash
python hypercode.py task "Research the impact of quantum computing on cryptography"
```

## Advanced Features
*   **Multi-Agent Collaboration**: Chain commands to involve multiple agents (e.g., "Research X, then have Frontend build a UI for it").
*   **System Telemetry**: View real-time infrastructure health alongside agent status.

## Troubleshooting
*   **No Response**: Check the `celery-worker` logs for errors. Ensure the `hypercode-core` API is reachable.
*   **Task Failed**: Review the task details in the database or via the API (`GET /api/v1/tasks/{id}`).
