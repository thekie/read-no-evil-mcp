"""List folders MCP tool."""

from read_no_evil_mcp.tools._app import mcp
from read_no_evil_mcp.tools._service import create_service


def list_folders_impl() -> str:
    """List all available email folders/mailboxes.

    Returns:
        A formatted list of folder names.
    """
    with create_service() as service:
        folders = service.list_folders()
        if not folders:
            return "No folders found."
        return "\n".join(f"- {f.name}" for f in folders)


@mcp.tool
def list_folders() -> str:
    """List all available email folders/mailboxes."""
    return list_folders_impl()
