"""Move email MCP tool."""

from read_no_evil_mcp.tools._app import mcp
from read_no_evil_mcp.tools._error_handler import handle_tool_errors
from read_no_evil_mcp.tools._service import create_securemailbox
from read_no_evil_mcp.tools._update_notice import append_update_notice


@mcp.tool
@append_update_notice
@handle_tool_errors
def move_email(account: str, folder: str, uid: int, target_folder: str) -> str:
    """Move an email to a target folder.

    Args:
        account: Account ID to use (e.g., "work", "personal").
        folder: Folder containing the email.
        uid: Unique identifier of the email.
        target_folder: Destination folder to move the email to.
    """
    if uid < 1:
        return "Invalid parameter: uid must be a positive integer"
    if not folder or not folder.strip():
        return "Invalid parameter: folder must not be empty"
    if not target_folder or not target_folder.strip():
        return "Invalid parameter: target_folder must not be empty"

    with create_securemailbox(account) as mailbox:
        success = mailbox.move_email(folder, uid, target_folder)

        if success:
            return f"Email {folder}/{uid} moved to {target_folder}."
        else:
            return f"Email not found: {folder}/{uid}"
