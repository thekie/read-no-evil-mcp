"""List folders tool implementation."""

from typing import Any, ClassVar

from mcp.types import TextContent

from read_no_evil_mcp.tools.base import BaseTool
from read_no_evil_mcp.tools.registry import register_tool


@register_tool
class ListFoldersTool(BaseTool):
    """Tool to list all available email folders/mailboxes."""

    name: ClassVar[str] = "list_folders"
    description: ClassVar[str] = "List all available email folders/mailboxes"
    input_schema: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the list_folders tool.

        Args:
            arguments: Empty dict (no parameters required)

        Returns:
            List containing a single TextContent with folder names
        """
        folders = self.service.list_folders()
        result = "\n".join(f"- {f.name}" for f in folders)
        return [TextContent(type="text", text=result or "No folders found.")]
