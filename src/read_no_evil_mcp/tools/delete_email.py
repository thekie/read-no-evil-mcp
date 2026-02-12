"""Delete email MCP tool."""

from read_no_evil_mcp.tools._app import mcp
from read_no_evil_mcp.tools._error_handler import handle_tool_errors
from read_no_evil_mcp.tools._service import create_securemailbox


@mcp.tool
@handle_tool_errors
def delete_email(account: str, folder: str, uid: int) -> str:
    """Delete an email by UID.

    Args:
        account: Account ID to use (e.g., "work", "personal").
        folder: Folder containing the email.
        uid: Unique identifier of the email.
    """
    if uid < 1:
        return "Invalid parameter: uid must be a positive integer"
    if not folder or not folder.strip():
        return "Invalid parameter: folder must not be empty"

    with create_securemailbox(account) as mailbox:
        success = mailbox.delete_email(folder, uid)
        if success:
            return f"Successfully deleted email {folder}/{uid}"
        return f"Failed to delete email {folder}/{uid}"
