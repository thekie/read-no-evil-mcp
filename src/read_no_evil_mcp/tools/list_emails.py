"""List emails MCP tool."""

from datetime import timedelta

from read_no_evil_mcp.accounts.config import AccessLevel
from read_no_evil_mcp.exceptions import PermissionDeniedError
from read_no_evil_mcp.tools._app import mcp
from read_no_evil_mcp.tools._service import create_securemailbox

# Mapping of access levels to markers shown in list output
ACCESS_MARKERS: dict[AccessLevel, str] = {
    AccessLevel.TRUSTED: " [TRUSTED]",
    AccessLevel.ASK_BEFORE_READ: " [ASK]",
    AccessLevel.SHOW: "",  # No marker for default level
}


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
    if days_back < 1:
        return "Invalid parameter: days_back must be a positive integer"
    if not folder or not folder.strip():
        return "Invalid parameter: folder must not be empty"
    if limit is not None and limit < 1:
        return "Invalid parameter: limit must be a positive integer"

    try:
        with create_securemailbox(account) as mailbox:
            secure_emails = mailbox.fetch_emails(
                folder,
                lookback=timedelta(days=days_back),
                limit=limit,
            )

            if not secure_emails:
                return "No emails found."

            lines = []
            for secure_email in secure_emails:
                email = secure_email.summary
                date_str = email.date.strftime("%Y-%m-%d %H:%M")
                attachment_marker = " [+]" if email.has_attachments else ""
                seen_marker = "" if email.is_seen else " [UNREAD]"

                # Get access marker from the enriched model
                access_marker = ACCESS_MARKERS.get(secure_email.access_level, "")

                # Build email line
                email_line = (
                    f"[{email.uid}] {date_str} | {email.sender.address} | "
                    f"{email.subject}{attachment_marker}{seen_marker}{access_marker}"
                )
                lines.append(email_line)

                # Add prompt if present in the enriched model
                if secure_email.prompt:
                    lines.append(f"    -> {secure_email.prompt}")

            return "\n".join(lines)
    except PermissionDeniedError as e:
        return f"Permission denied: {e}"
