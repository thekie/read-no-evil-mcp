"""Get email MCP tool."""

from read_no_evil_mcp.accounts.config import AccessLevel
from read_no_evil_mcp.exceptions import PermissionDeniedError
from read_no_evil_mcp.filtering.access_rules import (
    AccessRuleMatcher,
    get_read_prompt,
)
from read_no_evil_mcp.mailbox import PromptInjectionError
from read_no_evil_mcp.models import Email
from read_no_evil_mcp.tools._app import mcp
from read_no_evil_mcp.tools._service import create_securemailbox, get_account_config

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
        config = get_account_config(account)
        access_matcher = AccessRuleMatcher(
            sender_rules=config.sender_rules,
            subject_rules=config.subject_rules,
        )

        with create_securemailbox(account) as mailbox:
            try:
                email_result: Email | None = mailbox.get_email(folder, uid)
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

            # Get access level for the email
            access_level = access_matcher.get_access_level(
                email_result.sender.address, email_result.subject
            )

            lines = [
                f"Subject: {email_result.subject}",
                f"From: {email_result.sender}",
                f"To: {', '.join(str(addr) for addr in email_result.to)}",
                f"Date: {email_result.date.strftime('%Y-%m-%d %H:%M:%S')}",
                f"Status: {'Read' if email_result.is_seen else 'Unread'}",
            ]

            # Add access level for trusted and ask_before_read
            if access_level in ACCESS_DISPLAY:
                lines.append(f"Access: {ACCESS_DISPLAY[access_level]}")
                # Add prompt if configured
                prompt = get_read_prompt(access_level, config.read_prompts)
                if prompt:
                    lines.append(f"-> {prompt}")

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
    except PermissionDeniedError as e:
        return f"Permission denied: {e}"
