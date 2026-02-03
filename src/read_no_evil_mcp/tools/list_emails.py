"""List emails MCP tool."""

from datetime import timedelta

from read_no_evil_mcp.tools._app import mcp
from read_no_evil_mcp.tools._service import create_service


def list_emails_impl(
    folder: str = "INBOX",
    days_back: int = 7,
    limit: int | None = None,
) -> str:
    """List email summaries from a folder.

    Args:
        folder: Folder to list emails from (default: INBOX).
        days_back: Number of days to look back (default: 7).
        limit: Maximum number of emails to return.

    Returns:
        A formatted list of email summaries.
    """
    with create_service() as service:
        emails = service.fetch_emails(
            folder,
            lookback=timedelta(days=days_back),
            limit=limit,
        )

        if not emails:
            return "No emails found."

        lines = []
        for email in emails:
            date_str = email.date.strftime("%Y-%m-%d %H:%M")
            attachment_marker = " [+]" if email.has_attachments else ""
            lines.append(
                f"[{email.uid}] {date_str} | {email.sender.address} | "
                f"{email.subject}{attachment_marker}"
            )

        return "\n".join(lines)


@mcp.tool
def list_emails(
    folder: str = "INBOX",
    days_back: int = 7,
    limit: int | None = None,
) -> str:
    """List email summaries from a folder.

    Args:
        folder: Folder to list emails from (default: INBOX).
        days_back: Number of days to look back (default: 7).
        limit: Maximum number of emails to return.
    """
    return list_emails_impl(folder, days_back, limit)
