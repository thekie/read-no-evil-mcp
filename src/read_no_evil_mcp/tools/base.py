"""Abstract base class for MCP tools."""

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from mcp.types import TextContent

from read_no_evil_mcp.service import EmailService


class BaseTool(ABC):
    """Abstract base class defining the interface for MCP tools.

    Subclasses must define class-level attributes for name, description,
    and input_schema, and implement the execute method.

    Usage:
        @register_tool
        class MyTool(BaseTool):
            name = "my_tool"
            description = "Does something useful"
            input_schema = {"type": "object", "properties": {}, "required": []}

            def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
                ...
    """

    name: ClassVar[str]
    description: ClassVar[str]
    input_schema: ClassVar[dict[str, Any]]

    def __init__(self, service: EmailService) -> None:
        """Initialize the tool with an EmailService instance.

        Args:
            service: Connected EmailService for email operations
        """
        self.service = service

    @abstractmethod
    def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the tool with the given arguments.

        Args:
            arguments: Tool arguments matching the input_schema

        Returns:
            List of TextContent results
        """
        ...
