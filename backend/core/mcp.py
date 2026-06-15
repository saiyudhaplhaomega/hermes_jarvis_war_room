"""
MCP (Model Context Protocol) Tool Node for Hermes.

Standardizes agent-to-tool communication across LangGraph and CrewAI.
"""
from __future__ import annotations

from langchain.tools import StructuredTool
from typing import Callable, Optional

class MCPTool:
    """MCP-compatible tool wrapper."""

    def __init__(self, name: str, description: str, func: Callable):
        self.name = name
        self.description = description
        self.func = func

    def to_structured_tool(self) -> StructuredTool:
        """Convert to LangChain StructuredTool."""
        return StructuredTool.from_function(
            func=self.func,
            name=self.name,
            description=self.description
        )

# Example tools
web_search = MCPTool(
    name="web_search",
    description="Search the web for information.",
    func=lambda query: {"results": [{"url": "https://example.com", "title": query}]}
)

kanban_update = MCPTool(
    name="kanban_update",
    description="Update a Kanban task.",
    func=lambda task_id, status: {"success": True, "task_id": task_id, "status": status}
)

class DynamicMCPTool:
    """Zero-code MCP tool generation."""

    def __init__(self, tool_name: str, description: str, api_endpoint: str):
        self.tool_name = tool_name
        self.description = description
        self.api_endpoint = api_endpoint

    def generate(self) -> StructuredTool:
        """Generate a StructuredTool from API endpoint."""
        return StructuredTool.from_function(
            func=self._call_api,
            name=self.tool_name,
            description=self.description
        )

    def _call_api(self, **kwargs) -> dict:
        """Call the API endpoint."""
        import requests
        try:
            response = requests.post(
                self.api_endpoint,
                json=kwargs,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}

# Example usage
web_search_tool = DynamicMCPTool(
    tool_name="web_search",
    description="Search the web for information.",
    api_endpoint="http://localhost:18888/mcp/web_search"
).generate()
