"""Get email MCP tool."""

from read_no_evil_mcp.mailbox import PromptInjectionError
from read_no_evil_mcp.models import Email
from read_no_evil_mcp.tools._app import mcp
from read_no_evil_mcp.tools._service import create_securemailbox


@mcp.tool
def get_email(account: str, folder: str, uid: int) -> str:
    """Get full email content by UID.

    Args:
        account: Account ID to use (e.g., "work", "personal").
        folder: Folder containing the email.
        uid: Unique identifier of the email.
    """
    with create_securemailbox(account) as service:
        try:
            email_result: Email | None = service.get_email(folder, uid)
        except PromptInjectionError as e:
            patterns = ", ".join(e.scan_result.detected_patterns)
            return (
                f"BLOCKED: Email {folder}/{uid} contains suspected prompt injection.\n"
                f"Detected patterns: {patterns}\n"
                f"Score: {e.scan_result.score:.2f}\n\n"
                "This email has been blocked to protect against prompt injection attacks."
            )

        if not email_result:
            return f"Email not found: {folder}/{uid}"

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

        return "\n".join(lines)
