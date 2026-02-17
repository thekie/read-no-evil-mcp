"""List emails MCP tool."""

from datetime import timedelta

from read_no_evil_mcp.accounts.config import AccessLevel
from read_no_evil_mcp.tools._app import mcp
from read_no_evil_mcp.tools._error_handler import handle_tool_errors
from read_no_evil_mcp.tools._service import create_securemailbox
from read_no_evil_mcp.tools._update_notice import append_update_notice

# Mapping of access levels to markers shown in list output
ACCESS_MARKERS: dict[AccessLevel, str] = {
    AccessLevel.TRUSTED: " [TRUSTED]",
    AccessLevel.ASK_BEFORE_READ: " [ASK]",
    AccessLevel.SHOW: "",  # No marker for default level
}


@mcp.tool
@append_update_notice
@handle_tool_errors
def list_emails(
    account: str,
    folder: str = "INBOX",
    days_back: int = 7,
    limit: int | None = None,
    offset: int = 0,
    unread_only: bool = False,
) -> str:
    """List email summaries from a folder.

    Args:
        account: Account ID to use (e.g., "work", "personal").
        folder: Folder to list emails from (default: INBOX).
        days_back: Number of days to look back (default: 7).
        limit: Maximum number of emails to return.
        offset: Number of emails to skip for pagination (default: 0).
        unread_only: Only return unread emails (default: False).
    """
    if days_back < 1:
        return "Invalid parameter: days_back must be a positive integer"
    if not folder or not folder.strip():
        return "Invalid parameter: folder must not be empty"
    if limit is not None and limit < 1:
        return "Invalid parameter: limit must be a positive integer"
    if offset < 0:
        return "Invalid parameter: offset must be a non-negative integer"

    with create_securemailbox(account) as mailbox:
        result = mailbox.fetch_emails(
            folder,
            lookback=timedelta(days=days_back),
            limit=limit,
            offset=offset,
            unread_only=unread_only,
        )

        if not result.items:
            return "No emails found."

        lines = []
        for secure_email in result.items:
            email = secure_email.summary
            date_str = email.date.strftime("%Y-%m-%d %H:%M")
            attachment_marker = " [+]" if email.has_attachments else ""
            seen_marker = "" if email.is_seen else " [UNREAD]"

            # Get access marker from the enriched model
            access_marker = ACCESS_MARKERS.get(secure_email.access_level, "")
            unscanned_marker = " [UNSCANNED]" if secure_email.protection_skipped else ""

            # Build email line
            email_line = (
                f"[{email.uid}] {date_str} | {email.sender.address} | "
                f"{email.subject}{attachment_marker}{seen_marker}{access_marker}"
                f"{unscanned_marker}"
            )
            lines.append(email_line)

            # Add prompt if present in the enriched model
            if secure_email.prompt:
                lines.append(f"    -> {secure_email.prompt}")

        # Show filtering summary if any emails were filtered
        filter_parts: list[str] = []
        if result.blocked_count > 0:
            noun = "email" if result.blocked_count == 1 else "emails"
            filter_parts.append(f"{result.blocked_count} {noun} blocked by security filter")
        if result.hidden_count > 0:
            noun = "email" if result.hidden_count == 1 else "emails"
            filter_parts.append(f"{result.hidden_count} {noun} hidden by sender rules")
        if filter_parts:
            lines.append(f"\nNote: {', '.join(filter_parts)}")

        shown = len(result.items)
        if shown < result.total:
            next_offset = offset + shown
            lines.append(
                f"\nShowing {shown} of {result.total} emails. Use offset={next_offset} to see more."
            )

        return "\n".join(lines)
