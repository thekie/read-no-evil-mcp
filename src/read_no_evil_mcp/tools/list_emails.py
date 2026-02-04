"""List emails MCP tool."""

from datetime import timedelta

from read_no_evil_mcp.exceptions import PermissionDeniedError
from read_no_evil_mcp.tools._app import mcp
from read_no_evil_mcp.tools._service import create_securemailbox, get_permission_checker


@mcp.tool
def list_emails(
    account: str,
    folder: str = "INBOX",
    days_back: int = 7,
    limit: int | None = None,
) -> str:
    """List email summaries from a folder.

    Args:
        account: Account ID to use (e.g., "work", "personal").
        folder: Folder to list emails from (default: INBOX).
        days_back: Number of days to look back (default: 7).
        limit: Maximum number of emails to return.
    """
    try:
        checker = get_permission_checker(account)
        checker.check_read()
        checker.check_folder(folder)
    except PermissionDeniedError as e:
        return f"Permission denied: {e}"

    with create_securemailbox(account) as service:
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
