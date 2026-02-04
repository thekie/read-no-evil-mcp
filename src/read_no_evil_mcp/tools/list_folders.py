"""List folders MCP tool."""

from read_no_evil_mcp.exceptions import PermissionDeniedError
from read_no_evil_mcp.tools._app import mcp
from read_no_evil_mcp.tools._service import create_securemailbox, get_permission_checker


@mcp.tool
def list_folders(account: str) -> str:
    """List all available email folders/mailboxes.

    Args:
        account: Account ID to use (e.g., "work", "personal").
    """
    try:
        checker = get_permission_checker(account)
        checker.check_read()
    except PermissionDeniedError as e:
        return f"Permission denied: {e}"

    with create_securemailbox(account) as service:
        folders = service.list_folders()
        if not folders:
            return "No folders found."
        return "\n".join(f"- {f.name}" for f in folders)
