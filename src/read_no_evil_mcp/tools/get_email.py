"""Get email MCP tool."""

from read_no_evil_mcp.accounts.config import AccessLevel
from read_no_evil_mcp.exceptions import PermissionDeniedError
from read_no_evil_mcp.mailbox import PromptInjectionError
from read_no_evil_mcp.tools._app import mcp
from read_no_evil_mcp.tools._service import create_securemailbox

# Mapping of access levels to display names
ACCESS_DISPLAY: dict[AccessLevel, str] = {
    AccessLevel.TRUSTED: "TRUSTED",
    AccessLevel.ASK_BEFORE_READ: "ASK_BEFORE_READ",
}


@mcp.tool
def get_email(account: str, folder: str, uid: int) -> str:
    """Get full email content by UID.

    Args:
        account: Account ID to use (e.g., "work", "personal").
        folder: Folder containing the email.
        uid: Unique identifier of the email.
    """
    try:
        with create_securemailbox(account) as mailbox:
            try:
                secure_email = mailbox.get_email(folder, uid)
            except PromptInjectionError as e:
                patterns = ", ".join(e.scan_result.detected_patterns)
                return (
                    f"BLOCKED: Email {folder}/{uid} contains suspected prompt injection.\n"
                    f"Detected patterns: {patterns}\n"
                    f"Score: {e.scan_result.score:.2f}\n\n"
                    "This email has been blocked to protect against prompt injection attacks."
                )

            if not secure_email:
                return f"Email not found: {folder}/{uid}"

            email = secure_email.email
            lines = [
                f"Subject: {email.subject}",
                f"From: {email.sender}",
                f"To: {', '.join(str(addr) for addr in email.to)}",
                f"Date: {email.date.strftime('%Y-%m-%d %H:%M:%S')}",
                f"Status: {'Read' if email.is_seen else 'Unread'}",
            ]

            # Add access level for trusted and ask_before_read
            if secure_email.access_level in ACCESS_DISPLAY:
                lines.append(f"Access: {ACCESS_DISPLAY[secure_email.access_level]}")
                # Add prompt if present in the enriched model
                if secure_email.prompt:
                    lines.append(f"-> {secure_email.prompt}")

            if email.cc:
                lines.append(f"CC: {', '.join(str(addr) for addr in email.cc)}")

            if email.message_id:
                lines.append(f"Message-ID: {email.message_id}")

            if email.attachments:
                att_list = ", ".join(a.filename for a in email.attachments)
                lines.append(f"Attachments: {att_list}")

            lines.append("")  # Empty line before body

            if email.body_plain:
                lines.append(email.body_plain)
            elif email.body_html:
                lines.append("[HTML content - plain text not available]")
                lines.append(email.body_html)
            else:
                lines.append("[No body content]")

            return "\n".join(lines)
    except PermissionDeniedError as e:
        return f"Permission denied: {e}"
