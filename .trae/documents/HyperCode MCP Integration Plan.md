# MCP Integration Plan

## 1. Configuration & Dependencies
- **Create `agents/mcp-config.json`**: Define the Docker MCP server configuration.
- **Update `agents/coder/requirements.txt`**: Add `mcp` library.
- **Update `agents/coder/Dockerfile`**: Install Docker CLI (`docker.io`) to allow the agent to spawn sibling containers via the Docker socket.

## 2. Infrastructure (docker-compose.yml)
- **Add `mcp-server` service**: Deploy the standalone `docker/cagent-mcp-server` as requested.
- **Update `coder-agent` service**:
  - Mount `/var/run/docker.sock:/var/run/docker.sock` (Essential for "hands").
  - Ensure dependency on `mcp-server` (if we decide to use the service) or just ensure network connectivity.

## 3. CoderAgent Refactoring (`agents/coder/main.py`)
- **Import MCP SDK**: `mcp.client.stdio`, `StdioServerParameters`.
- **Initialize MCP Client**: Add `initialize_mcp()` method to start the Docker MCP session.
- **Implement New Capabilities**:
  - Add `analyze_with_docker_access(code)` method.
  - Integrate with existing `on_task` handler to route tasks to MCP-enabled logic.
  - Implement `call_docker_tool` helper to wrap MCP tool execution.

## 4. Verification
- **Build**: Rebuild `coder-agent` image with new dependencies.
- **Deploy**: Restart stack with `docker-compose up -d`.
- **Test**:
  - Verify `coder-agent` can see the Docker socket.
  - Trigger a test task (simulated) to verify MCP client connection.

## 5. Execution Order
1.  Create/Edit Config Files (`mcp-config.json`, `requirements.txt`).
2.  Update Dockerfile.
3.  Update `docker-compose.yml`.
4.  Refactor `main.py`.
5.  Build and Restart.
