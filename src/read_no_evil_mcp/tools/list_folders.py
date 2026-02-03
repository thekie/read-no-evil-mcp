"""List folders MCP tool."""

from read_no_evil_mcp.tools._app import mcp
from read_no_evil_mcp.tools._service import create_securemailbox


@mcp.tool
def list_folders() -> str:
    """List all available email folders/mailboxes."""
    with create_securemailbox() as service:
        folders = service.list_folders()
        if not folders:
            return "No folders found."
        return "\n".join(f"- {f.name}" for f in folders)
