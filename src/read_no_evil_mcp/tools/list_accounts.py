"""List accounts MCP tool."""

from read_no_evil_mcp.tools._app import mcp
from read_no_evil_mcp.tools._service import list_configured_accounts
from read_no_evil_mcp.tools._update_notice import append_update_notice


@mcp.tool
@append_update_notice
def list_accounts() -> str:
    """List all configured email account IDs.

    Use this to discover which accounts are available before calling other
    email tools like list_emails, get_email, or list_folders.

    Returns:
        A newline-separated list of account IDs.
    """
    accounts = list_configured_accounts()
    if not accounts:
        return "No accounts configured."
    return "\n".join(f"- {account}" for account in accounts)
