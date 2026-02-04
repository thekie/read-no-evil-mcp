"""Send email MCP tool."""

from read_no_evil_mcp.exceptions import PermissionDeniedError
from read_no_evil_mcp.tools._app import mcp
from read_no_evil_mcp.tools._service import create_securemailbox


@mcp.tool
def send_email(
    account: str,
    to: list[str],
    subject: str,
    body: str,
    cc: list[str] | None = None,
) -> str:
    """Send an email.

    Args:
        account: Account ID to use (e.g., "work", "personal").
        to: List of recipient email addresses.
        subject: Email subject line.
        body: Email body text (plain text).
        cc: Optional list of CC recipients.
    """
    try:
        with create_securemailbox(account) as mailbox:
            mailbox.send_email(
                to=to,
                subject=subject,
                body=body,
                cc=cc,
            )
            recipients = ", ".join(to)
            if cc:
                recipients += f" (CC: {', '.join(cc)})"
            return f"Email sent successfully to {recipients}"
    except PermissionDeniedError as e:
        return f"Permission denied: {e}"
    except RuntimeError as e:
        return f"Error: {e}"
