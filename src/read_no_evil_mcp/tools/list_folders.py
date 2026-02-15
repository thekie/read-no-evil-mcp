"""List folders MCP tool."""

from read_no_evil_mcp.tools._app import mcp
from read_no_evil_mcp.tools._error_handler import handle_tool_errors
from read_no_evil_mcp.tools._service import create_securemailbox


@mcp.tool
@handle_tool_errors
def list_folders(account: str) -> str:
    """List all available email folders/mailboxes.

    Args:
        account: Account ID to use (e.g., "work", "personal").
    """
    with create_securemailbox(account) as mailbox:
        folders = mailbox.list_folders()
        if not folders:
            return "No folders found."
        return "\n".join(f"- {f.name}" for f in folders)
