"""Mark spam MCP tool."""

from read_no_evil_mcp.exceptions import PermissionDeniedError
from read_no_evil_mcp.tools._app import mcp
from read_no_evil_mcp.tools._service import create_securemailbox


@mcp.tool
def mark_spam(account: str, folder: str, uid: int) -> str:
    """Mark an email as spam by moving it to the spam folder.

    Args:
        account: Account ID to use (e.g., "work", "personal").
        folder: Folder containing the email.
        uid: Unique identifier of the email.
    """
    try:
        with create_securemailbox(account) as mailbox:
            success = mailbox.mark_spam(folder, uid)

            if success:
                return f"Email {folder}/{uid} marked as spam."
            else:
                return f"Email not found: {folder}/{uid}"
    except PermissionDeniedError as e:
        return f"Permission denied: {e}"
    except RuntimeError as e:
        return f"Error: {e}"
