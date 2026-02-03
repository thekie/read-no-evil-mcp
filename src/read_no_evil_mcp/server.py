"""MCP server implementation for read-no-evil-mcp using FastMCP."""

from datetime import timedelta

from fastmcp import FastMCP

from read_no_evil_mcp.config import Settings
from read_no_evil_mcp.connectors.imap import IMAPConnector
from read_no_evil_mcp.models import Email, IMAPConfig
from read_no_evil_mcp.service import EmailService

# Create the FastMCP server instance
mcp = FastMCP(name="read-no-evil-mcp")


def _create_service() -> EmailService:
    """Create an EmailService from environment configuration."""
    settings = Settings()  # type: ignore[call-arg]
    config = IMAPConfig(
        host=settings.imap_host,
        port=settings.imap_port,
        username=settings.imap_username,
        password=settings.imap_password,
        ssl=settings.imap_ssl,
    )
    connector = IMAPConnector(config)
    return EmailService(connector)


def _list_folders_impl() -> str:
    """List all available email folders/mailboxes.

    Returns:
        A formatted list of folder names.
    """
    service = _create_service()
    try:
        service.connect()
        folders = service.list_folders()
        if not folders:
            return "No folders found."
        return "\n".join(f"- {f.name}" for f in folders)
    finally:
        service.disconnect()


def _list_emails_impl(
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
    service = _create_service()
    try:
        service.connect()
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
    finally:
        service.disconnect()


def _get_email_impl(folder: str, uid: int) -> str:
    """Get full email content by UID.

    Args:
        folder: Folder containing the email.
        uid: Unique identifier of the email.

    Returns:
        Formatted email content or error message if not found.
    """
    service = _create_service()
    try:
        service.connect()
        email_result: Email | None = service.get_email(folder, uid)

        if not email_result:
            return f"Email not found: {folder}/{uid}"

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

        return "\n".join(lines)
    finally:
        service.disconnect()


# Register tools with FastMCP
@mcp.tool
def list_folders() -> str:
    """List all available email folders/mailboxes."""
    return _list_folders_impl()


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
    return _list_emails_impl(folder, days_back, limit)


@mcp.tool
def get_email(folder: str, uid: int) -> str:
    """Get full email content by UID.

    Args:
        folder: Folder containing the email.
        uid: Unique identifier of the email.
    """
    return _get_email_impl(folder, uid)


def main() -> None:
    """Entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
