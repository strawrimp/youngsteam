"""Tool registry for agent tool use."""

from tools.base_tool import BaseTool, ToolResult
from tools.web_search import WebSearchTool
from tools.code_executor import CodeExecutorTool

__all__ = ["BaseTool", "ToolResult", "WebSearchTool", "CodeExecutorTool", "get_all_tools"]


def get_all_tools() -> list["BaseTool"]:
    """Return all available tools."""
    return [
        WebSearchTool(),
        CodeExecutorTool(),
    ]
