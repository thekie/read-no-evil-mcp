"""List emails tool implementation."""

from datetime import timedelta
from typing import Any, ClassVar

from mcp.types import TextContent

from read_no_evil_mcp.tools.base import BaseTool
from read_no_evil_mcp.tools.registry import register_tool


@register_tool
class ListEmailsTool(BaseTool):
    """Tool to list email summaries from a folder."""

    name: ClassVar[str] = "list_emails"
    description: ClassVar[str] = "List email summaries from a folder"
    input_schema: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "folder": {
                "type": "string",
                "description": "Folder to list emails from (default: INBOX)",
                "default": "INBOX",
            },
            "days_back": {
                "type": "integer",
                "description": "Number of days to look back (default: 7)",
                "default": 7,
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of emails to return",
            },
        },
        "required": [],
    }

    def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the list_emails tool.

        Args:
            arguments: Dict with optional folder, days_back, and limit

        Returns:
            List containing a single TextContent with email summaries
        """
        folder = arguments.get("folder", "INBOX")
        days_back = arguments.get("days_back", 7)
        limit = arguments.get("limit")

        emails = self.service.fetch_emails(
            folder,
            lookback=timedelta(days=days_back),
            limit=limit,
        )

        if not emails:
            return [TextContent(type="text", text="No emails found.")]

        lines = []
        for email in emails:
            date_str = email.date.strftime("%Y-%m-%d %H:%M")
            attachment_marker = " [+]" if email.has_attachments else ""
            lines.append(
                f"[{email.uid}] {date_str} | {email.sender.address} | "
                f"{email.subject}{attachment_marker}"
            )

        return [TextContent(type="text", text="\n".join(lines))]
