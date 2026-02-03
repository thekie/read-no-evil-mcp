"""Tools registry with auto-discovery and decorator-based registration."""

# isort: skip_file

from read_no_evil_mcp.tools.base import BaseTool
from read_no_evil_mcp.tools.registry import (
    execute_tool,
    get_all_tools,
    get_tool_names,
    register_tool,
)

# Import tool modules to trigger registration via decorators
# These must be imported after registry to avoid circular imports
from read_no_evil_mcp.tools import get_email as _get_email  # noqa: F401
from read_no_evil_mcp.tools import list_emails as _list_emails  # noqa: F401
from read_no_evil_mcp.tools import list_folders as _list_folders  # noqa: F401

__all__ = [
    "BaseTool",
    "execute_tool",
    "get_all_tools",
    "get_tool_names",
    "register_tool",
]
