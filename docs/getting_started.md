# Getting Started with HyperCode V2.0

> **built with WelshDog + BROski 🚀🌙**

Welcome to HyperCode V2.0! This guide will take you from `git clone` to your first "Hello World" deployment.

## Prerequisites

- **Docker & Docker Compose:** Ensure Docker Desktop is running (v4.0+).
- **Git:** For version control.
- **Node.js (v18+)**: Optional, only required if you plan to develop the frontend locally.

## Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/welshDog/HyperCode-V2.0.git
   cd HyperCode-V2.0
   ```

2. **Environment Setup**
   Copy the example environment file to create your local configuration:
   ```bash
   cp .env.example .env
   ```
   *Important: Open `.env` and add your `PERPLEXITY_API_KEY` or `OPENAI_API_KEY` to enable AI agent capabilities.*

3. **Start the Stack**
   Launch the entire ecosystem (Agents, API, DB, Observability):
   ```bash
   docker compose up -d
   ```

4. **Verify Installation**
   Check if all 23+ containers are running and healthy:
   ```bash
   docker compose ps
   ```
   You should see services like `hypercode-core`, `broski-terminal`, `hypercode-ollama`, `postgres`, and `redis` in a `healthy` state.

## Hello World Walkthrough

1. **Access the Interface**
   Open your browser and navigate to `http://localhost:3000`.

2. **Trigger a Simple Task**
   - Navigate to the **Agents** tab.
   - Select **Coder Agent**.
   - Input: `"Create a Python script that prints 'Hello, HyperCode!'"`.

3. **Observe Execution**
   - Watch the agent analyze the request.
   - See the code generation in real-time.
   - View the execution output in the terminal window.

## Common Issues

- **Docker Memory:** Ensure Docker has at least 4GB of RAM allocated.
- **Missing API Keys:** If agents fail to respond, check your `.env` file for valid API keys.
- **Port Conflicts:** Ensure ports 3000, 3001, 8000, and 5432 are free on your machine.

## Next Steps

- Review the [Architecture](architecture.md) to understand the system.
- Check the [API Reference](api_reference.md) for integration details.
- Read the [Runbook](../runbook.md) for operational procedures.

---
> **built with WelshDog + BROski 🚀🌙**
