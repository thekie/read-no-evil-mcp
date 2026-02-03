"""Get email tool implementation."""

from typing import Any, ClassVar

from mcp.types import TextContent

from read_no_evil_mcp.models import Email
from read_no_evil_mcp.tools.base import BaseTool
from read_no_evil_mcp.tools.registry import register_tool


@register_tool
class GetEmailTool(BaseTool):
    """Tool to get full email content by UID."""

    name: ClassVar[str] = "get_email"
    description: ClassVar[str] = "Get full email content by UID"
    input_schema: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "folder": {
                "type": "string",
                "description": "Folder containing the email",
            },
            "uid": {
                "type": "integer",
                "description": "Unique identifier of the email",
            },
        },
        "required": ["folder", "uid"],
    }

    def execute(self, arguments: dict[str, Any]) -> list[TextContent]:
        """Execute the get_email tool.

        Args:
            arguments: Dict with required folder and uid

        Returns:
            List containing a single TextContent with full email content
        """
        folder = arguments["folder"]
        uid = arguments["uid"]

        email_result: Email | None = self.service.get_email(folder, uid)

        if not email_result:
            return [TextContent(type="text", text=f"Email not found: {folder}/{uid}")]

        # Format email content
        lines = [
            f"Subject: {email_result.subject}",
            f"From: {email_result.sender}",
            f"To: {', '.join(str(addr) for addr in email_result.to)}",
            f"Date: {email_result.date.strftime('%Y-%m-%d %H:%M:%S')}",
        ]

        if email_result.cc:
            lines.append(f"CC: {', '.join(str(addr) for addr in email_result.cc)}")

        if email_result.message_id:
            lines.append(f"Message-ID: {email_result.message_id}")

        if email_result.attachments:
            att_list = ", ".join(a.filename for a in email_result.attachments)
            lines.append(f"Attachments: {att_list}")

        lines.append("")  # Empty line before body

        if email_result.body_plain:
            lines.append(email_result.body_plain)
        elif email_result.body_html:
            lines.append("[HTML content - plain text not available]")
            lines.append(email_result.body_html)
        else:
            lines.append("[No body content]")

        return [TextContent(type="text", text="\n".join(lines))]
