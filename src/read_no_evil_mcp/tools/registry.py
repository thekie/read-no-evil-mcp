"""Tool registry for decorator-based registration."""

from typing import Any

from mcp.types import TextContent, Tool

from read_no_evil_mcp.service import EmailService
from read_no_evil_mcp.tools.base import BaseTool

# Global registry of tool classes
_tool_registry: dict[str, type[BaseTool]] = {}


def register_tool(cls: type[BaseTool]) -> type[BaseTool]:
    """Decorator to register a tool class in the global registry.

    Usage:
        @register_tool
        class MyTool(BaseTool):
            ...
    """
    _tool_registry[cls.name] = cls
    return cls


def get_all_tools() -> list[Tool]:
    """Get MCP Tool definitions for all registered tools."""
    return [
        Tool(
            name=tool_cls.name,
            description=tool_cls.description,
            inputSchema=tool_cls.input_schema,
        )
        for tool_cls in _tool_registry.values()
    ]


def execute_tool(name: str, arguments: dict[str, Any], service: EmailService) -> list[TextContent]:
    """Execute a registered tool by name.

    Args:
        name: The tool name to execute
        arguments: The arguments to pass to the tool
        service: The EmailService instance to use

    Returns:
        List of TextContent results

    Raises:
        KeyError: If the tool is not found
    """
    if name not in _tool_registry:
        raise KeyError(f"Unknown tool: {name}")

    tool_cls = _tool_registry[name]
    tool = tool_cls(service)
    return tool.execute(arguments)


def get_tool_names() -> list[str]:
    """Get list of all registered tool names."""
    return list(_tool_registry.keys())
