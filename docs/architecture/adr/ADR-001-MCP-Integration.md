# Architecture Decision Record: MCP Integration for CoderAgent

## Status
Accepted

## Context
We needed a way for the CoderAgent to not just generate code, but also execute, test, and deploy it. Previous approaches involved building custom API wrappers around the Docker SDK, which were brittle and hard to maintain.

## Decision
We decided to integrate the **Model Context Protocol (MCP)** standard, specifically using the **Docker MCP Server**.

### Key Choices:
1.  **Protocol**: Used MCP (PERPLEXITY's standard) to future-proof the agent interface.
2.  **Transport**: Used `stdio` transport to run the MCP server as a subprocess within the agent container (via `docker run` or direct python package execution).
3.  **Permissions**: Mounted the host Docker socket to the agent container.

## Consequences

### Positive
- **Standardization**: We can easily swap out the underlying Docker tool for other MCP-compatible tools (e.g., Kubernetes, GitHub).
- **Autonomy**: The agent can now perform end-to-end DevOps tasks without human intervention.
- **Simplicity**: Reduced custom wrapper code in favor of standardized tool calls.

### Negative
- **Security Risk**: Granting the agent access to the Docker socket gives it root-equivalent access to the host. This requires strict prompt engineering and future sandboxing.
- **Complexity**: Debugging MCP connection issues across container boundaries can be complex.

## Compliance
- **Neurodivergent-First**: Reduces cognitive load by automating complex deployment steps.
- **High Performance**: Direct socket communication is low-latency.

---
> *Built with WelshDog + BROski* 🚀🌙
