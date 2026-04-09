"""Abstract base class for all agent tools."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ToolResult:
    """Result returned from a tool execution."""
    success: bool
    output: str
    error: str = ""
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_string(self) -> str:
        if self.success:
            return self.output
        return f"[Error] {self.error}"


class BaseTool(ABC):
    """Abstract base class for all agent tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name (used in function call schema)."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description shown to the LLM."""
        ...

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """JSON Schema of tool parameters."""
        ...

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        ...

    def to_function_schema(self) -> Dict[str, Any]:
        """Return OpenAI/DeepSeek-compatible function calling schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            }
        }
