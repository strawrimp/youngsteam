"""Tool registry for agent tool use."""

from config import settings
from tools.base_tool import BaseTool, ToolResult
from tools.web_search import WebSearchTool
from tools.web_scrape import WebScrapeTool
from tools.code_executor import CodeExecutorTool
from tools.youtube_transcript import YouTubeTranscriptTool
from tools.file_operations import FileOperationsTool
from tools.openclaw_tool import OpenClawTool

__all__ = [
    "BaseTool",
    "ToolResult",
    "WebSearchTool",
    "WebScrapeTool",
    "CodeExecutorTool",
    "YouTubeTranscriptTool",
    "FileOperationsTool",
    "OpenClawTool",
    "get_all_tools",
]


def get_all_tools() -> list["BaseTool"]:
    """Return all available tools."""
    tools = [
        WebSearchTool(),
        WebScrapeTool(),
        CodeExecutorTool(),
        YouTubeTranscriptTool(),
        FileOperationsTool(),
    ]

    if getattr(settings, "openclaw_enabled", False):
        tools.append(OpenClawTool())

    return tools
