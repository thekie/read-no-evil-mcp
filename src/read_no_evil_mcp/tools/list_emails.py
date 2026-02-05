"""List emails MCP tool."""

from datetime import timedelta

from read_no_evil_mcp.accounts.config import AccessLevel
from read_no_evil_mcp.exceptions import PermissionDeniedError
from read_no_evil_mcp.filtering.access_rules import (
    AccessRuleMatcher,
    get_list_prompt,
)
from read_no_evil_mcp.tools._app import mcp
from read_no_evil_mcp.tools._service import create_securemailbox, get_account_config

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
    try:
        config = get_account_config(account)
        access_matcher = AccessRuleMatcher(
            sender_rules=config.sender_rules,
            subject_rules=config.subject_rules,
        )

        with create_securemailbox(account) as mailbox:
            emails = mailbox.fetch_emails(
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
                seen_marker = "" if email.is_seen else " [UNREAD]"

                # Get access level and marker
                access_level = access_matcher.get_access_level(email.sender.address, email.subject)
                access_marker = ACCESS_MARKERS.get(access_level, "")

                # Build email line
                email_line = (
                    f"[{email.uid}] {date_str} | {email.sender.address} | "
                    f"{email.subject}{attachment_marker}{seen_marker}{access_marker}"
                )
                lines.append(email_line)

                # Add prompt if configured for this access level
                prompt = get_list_prompt(access_level, config.list_prompts)
                if prompt:
                    lines.append(f"    -> {prompt}")

            return "\n".join(lines)
    except PermissionDeniedError as e:
        return f"Permission denied: {e}"
