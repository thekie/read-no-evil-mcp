"""Move email MCP tool."""

from read_no_evil_mcp.exceptions import PermissionDeniedError
from read_no_evil_mcp.tools._app import mcp
from read_no_evil_mcp.tools._service import create_securemailbox


@mcp.tool
def move_email(account: str, folder: str, uid: int, target_folder: str) -> str:
    """Move an email to a target folder.

    Args:
        account: Account ID to use (e.g., "work", "personal").
        folder: Folder containing the email.
        uid: Unique identifier of the email.
        target_folder: Destination folder to move the email to.
    """
    try:
        with create_securemailbox(account) as mailbox:
            success = mailbox.move_email(folder, uid, target_folder)

            if success:
                return f"Email {folder}/{uid} moved to {target_folder}."
            else:
                return f"Email not found: {folder}/{uid}"
    except PermissionDeniedError as e:
        return f"Permission denied: {e}"
    except RuntimeError as e:
        return f"Error: {e}"
