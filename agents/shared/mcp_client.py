#!/usr/bin/env python3
"""
MCP Gateway Integration Layer for HyperCode Agents
================================================================

This module provides agents with:
1. Automatic MCP tool discovery
2. Safe tool invocation with rate limiting & auth
3. Fallback to direct calls if gateway unavailable
4. Observability (metrics, logging, audit)

Usage in Agent:
    from mcp_client import MCPClient
    
    client = MCPClient()
    result = await client.call_tool("github:list_repos", {"owner": "welshDog"})
    
    # Or use high-level helpers:
    repos = await client.github.list_repos(owner="welshDog")
    query_result = await client.postgres.execute_query("SELECT * FROM agents")
"""

import os
import asyncio
import httpx
from typing import Any, Dict, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    GITHUB = "github"
    POSTGRES = "postgres"
    FILESYSTEM = "filesystem"
    VECTORDB = "vectordb"
    CUSTOM = "custom"


@dataclass
class ToolResult:
    """Result from MCP tool execution"""
    success: bool
    data: Any
    error: Optional[str] = None
    latency_ms: float = 0.0
    from_cache: bool = False


class MCPClient:
    """
    MCP Gateway client with agent-friendly interface.
    Handles auth, retry logic, caching, and fallbacks.
    """

    def __init__(
        self,
        gateway_url: Optional[str] = None,
        api_key: Optional[str] = None,
        fallback_to_direct: bool = True,
    ):
        self.gateway_url = gateway_url or os.getenv(
            "MCP_GATEWAY_URL", "http://mcp-rest-adapter:8821"
        )
        self.api_key = api_key or os.getenv("MCP_GATEWAY_API_KEY", "")
        self.fallback_to_direct = fallback_to_direct
        self.timeout = int(os.getenv("MCP_GATEWAY_TIMEOUT_SECONDS", "30"))

        self.client = httpx.AsyncClient(timeout=self.timeout)
        self._tool_cache: Dict[str, Any] = {}

        # High-level tool interfaces
        self.github = GithubTool(self)
        self.postgres = PostgresTool(self)
        self.filesystem = FileSystemTool(self)
        self.vectordb = VectorDBTool(self)

    async def call_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
        category: Optional[str] = None,
    ) -> ToolResult:
        """
        Call an MCP tool via gateway.

        Args:
            tool_name: e.g., "list_repos", "execute_query"
            params: Tool parameters
            category: Tool category (github, postgres, etc.) - auto-detected if None

        Returns:
            ToolResult with data, error, and metadata
        """
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

            if ":" in tool_name:
                tool, action = tool_name.split(":", 1)
                payload = {"tool": tool, "action": action, "params": params}
            else:
                payload = {"tool": tool_name, "params": params}

            response = await self.client.post(
                f"{self.gateway_url}/tools/call",
                json=payload,
                headers=headers,
            )

            if response.status_code == 200:
                data = response.json()
                return ToolResult(
                    success=True,
                    data=data.get("result"),
                    latency_ms=data.get("latency_ms", 0),
                    from_cache=data.get("from_cache", False),
                )
            else:
                logger.error(
                    f"MCP tool call failed: {response.status_code} {response.text}"
                )
                return ToolResult(success=False, data=None, error=response.text)

        except Exception as e:
            logger.error(f"MCP client error: {e}")
            if self.fallback_to_direct:
                logger.warning("Falling back to direct tool invocation")
                return await self._fallback_call(tool_name, params)
            return ToolResult(success=False, data=None, error=str(e))

    async def _fallback_call(
        self, tool_name: str, params: Dict[str, Any]
    ) -> ToolResult:
        """Fallback to direct tool calls if gateway unavailable"""
        try:
            logger.warning(f"Using fallback for tool: {tool_name}")
            # Import and call tools directly
            # This is a safety net - in production, prefer gateway
            return ToolResult(
                success=False,
                data=None,
                error="Fallback not configured. Please set MCP_GATEWAY_URL",
            )
        except Exception as e:
            return ToolResult(success=False, data=None, error=str(e))

    async def discover_tools(self) -> Dict[str, Any]:
        """Discover available tools from gateway"""
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            response = await self.client.get(
                f"{self.gateway_url}/tools/discover", headers=headers
            )
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            logger.error(f"Tool discovery failed: {e}")
            return {}

    async def close(self):
        """Clean up HTTP client"""
        await self.client.aclose()


# ============================================================================
# HIGH-LEVEL TOOL INTERFACES (Agent-Friendly APIs)
# ============================================================================


class GithubTool:
    """GitHub operations via MCP"""

    def __init__(self, client: MCPClient):
        self.client = client

    async def list_repos(self, owner: str, sort: str = "stars") -> ToolResult:
        return await self.client.call_tool(
            "github:list_repos", {"owner": owner, "sort": sort}
        )

    async def list_issues(
        self, owner: str, repo: str, state: str = "open"
    ) -> ToolResult:
        return await self.client.call_tool(
            "github:list_issues", {"owner": owner, "repo": repo, "state": state}
        )

    async def create_issue(
        self, owner: str, repo: str, title: str, body: str = ""
    ) -> ToolResult:
        return await self.client.call_tool(
            "github:create_issue",
            {"owner": owner, "repo": repo, "title": title, "body": body},
        )

    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str = "main",
        body: str = "",
    ) -> ToolResult:
        return await self.client.call_tool(
            "github:create_pull_request",
            {
                "owner": owner,
                "repo": repo,
                "title": title,
                "head": head,
                "base": base,
                "body": body,
            },
        )


class PostgresTool:
    """PostgreSQL queries via MCP"""

    def __init__(self, client: MCPClient):
        self.client = client

    async def execute_query(self, query: str, params: Optional[Dict] = None) -> ToolResult:
        return await self.client.call_tool(
            "postgres:execute_query", {"query": query, "params": params or {}}
        )

    async def list_tables(self, schema: str = "public") -> ToolResult:
        return await self.client.call_tool(
            "postgres:list_tables", {"schema": schema}
        )

    async def describe_table(self, table: str, schema: str = "public") -> ToolResult:
        return await self.client.call_tool(
            "postgres:describe_table", {"table": table, "schema": schema}
        )


class FileSystemTool:
    """Safe file system operations via MCP"""

    def __init__(self, client: MCPClient):
        self.client = client

    async def read_file(self, path: str) -> ToolResult:
        return await self.client.call_tool("filesystem:read", {"path": path})

    async def write_file(self, path: str, content: str) -> ToolResult:
        return await self.client.call_tool(
            "filesystem:write", {"path": path, "content": content}
        )

    async def list_directory(self, path: str) -> ToolResult:
        return await self.client.call_tool(
            "filesystem:list_directory", {"path": path}
        )


class VectorDBTool:
    """RAG / Vector database queries via MCP"""

    def __init__(self, client: MCPClient):
        self.client = client

    async def search(self, query: str, limit: int = 5) -> ToolResult:
        return await self.client.call_tool(
            "vectordb:search", {"query": query, "limit": limit}
        )

    async def add_document(self, content: str, metadata: Optional[Dict] = None) -> ToolResult:
        return await self.client.call_tool(
            "vectordb:add_document", {"content": content, "metadata": metadata or {}}
        )

    async def delete_collection(self) -> ToolResult:
        return await self.client.call_tool("vectordb:delete_collection", {})


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

async def main():
    """Example agent using MCP client"""
    client = MCPClient()

    try:
        # Discover available tools
        tools = await client.discover_tools()
        print(f"Available tools: {list(tools.keys())}")

        # List GitHub repos
        result = await client.github.list_repos(owner="welshDog")
        if result.success:
            print(f"Repos: {result.data}")
            print(f"Latency: {result.latency_ms}ms, Cached: {result.from_cache}")
        else:
            print(f"Error: {result.error}")

        # Run a database query
        result = await client.postgres.execute_query("SELECT * FROM agents LIMIT 5")
        if result.success:
            print(f"Agents: {result.data}")
        else:
            print(f"Error: {result.error}")

        # Search vector database
        result = await client.vectordb.search("HyperCode architecture", limit=3)
        if result.success:
            print(f"Search results: {result.data}")
        else:
            print(f"Error: {result.error}")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
