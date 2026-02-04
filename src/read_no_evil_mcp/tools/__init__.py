"""MCP tools package.

This module re-exports the shared FastMCP instance and imports all tools
to trigger their registration.
"""

from read_no_evil_mcp.tools import get_email as _get_email
from read_no_evil_mcp.tools import list_accounts as _list_accounts
from read_no_evil_mcp.tools import list_emails as _list_emails
from read_no_evil_mcp.tools import list_folders as _list_folders
from read_no_evil_mcp.tools._app import mcp

__all__ = ["mcp"]

# Silence unused import warnings
del _get_email, _list_accounts, _list_emails, _list_folders
