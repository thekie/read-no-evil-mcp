"""MCP tools package.

This module re-exports the shared FastMCP instance and imports all tools
to trigger their registration.
"""

from read_no_evil_mcp.tools import get_email as _get_email  # noqa: F401
from read_no_evil_mcp.tools import list_accounts as _list_accounts  # noqa: F401
from read_no_evil_mcp.tools import list_emails as _list_emails  # noqa: F401
from read_no_evil_mcp.tools import list_folders as _list_folders  # noqa: F401
from read_no_evil_mcp.tools import send_email as _send_email  # noqa: F401
from read_no_evil_mcp.tools._app import mcp

__all__ = ["mcp"]
