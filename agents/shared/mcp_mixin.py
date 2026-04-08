from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any

router = APIRouter()

class Tool(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]

class MCPToolResponse(BaseModel):
    tools: List[Tool]

# This is a template mixin for agents to expose their tools
class MCPServerMixin:
    """
    Mixin to add MCP endpoints to an agent.
    Agents should inherit from this and BaseAgent.
    """
    def setup_mcp_routes(self):
        @self.app.get("/mcp/tools", response_model=MCPToolResponse)
        async def list_tools():
            """List available tools for this agent"""
            return {
                "tools": self.get_tools()
            }
        
        @self.app.post("/mcp/execute")
        async def execute_tool(tool_name: str, params: Dict[str, Any]):
            """Execute a specific tool"""
            return await self.execute_tool_logic(tool_name, params)

    def get_tools(self) -> List[Tool]:
        """Override this to return the agent's tools"""
        return []

    async def execute_tool_logic(self, tool_name: str, params: Dict[str, Any]):
        """Override this to execute the tool logic"""
        raise NotImplementedError("Agent must implement execute_tool_logic")
