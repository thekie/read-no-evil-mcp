"""Send email MCP tool."""

import base64
from pathlib import Path
from typing import Any, cast

from read_no_evil_mcp.email.models import OutgoingAttachment
from read_no_evil_mcp.tools._app import mcp
from read_no_evil_mcp.tools._error_handler import handle_tool_errors
from read_no_evil_mcp.tools._service import create_securemailbox
from read_no_evil_mcp.tools._update_notice import append_update_notice
from read_no_evil_mcp.tools.models import AttachmentInput


def _parse_attachments(
    attachment_inputs: list[AttachmentInput | dict[str, Any]] | None,
) -> list[OutgoingAttachment] | None:
    """Convert attachment inputs to OutgoingAttachment objects.

    Args:
        attachment_inputs: List of AttachmentInput objects or dicts from MCP input.

    Returns:
        List of OutgoingAttachment objects, or None if no attachments.

    Raises:
        ValueError: If attachment is missing required fields.
    """
    if not attachment_inputs:
        return None

    attachments: list[OutgoingAttachment] = []
    for item in attachment_inputs:
        # Convert dict to AttachmentInput if needed
        att = item if isinstance(item, AttachmentInput) else AttachmentInput(**item)

        if not att.content and not att.path:
            raise ValueError(f"Attachment '{att.filename}' must have either 'content' or 'path'")

        # Validate file path exists early to provide better error messages
        if att.path and not Path(att.path).exists():
            raise ValueError(f"Attachment file not found: {att.path}")

        content: bytes | None = None
        if att.content:
            content = base64.b64decode(att.content)

        attachments.append(
            OutgoingAttachment(
                filename=att.filename,
                content=content,
                mime_type=att.mime_type,
                path=att.path,
            )
        )

    return attachments


@mcp.tool
@append_update_notice
@handle_tool_errors
def send_email(
    account: str,
    to: list[str],
    subject: str,
    body: str,
    cc: list[str] | None = None,
    reply_to: str | None = None,
    attachments: list[AttachmentInput] | None = None,
) -> str:
    """Send an email with optional attachments.

    Args:
        account: Account ID to use (e.g., "work", "personal").
        to: List of recipient email addresses.
        subject: Email subject line.
        body: Email body text (plain text).
        cc: Optional list of CC recipients.
        reply_to: Optional Reply-To email address.
        attachments: Optional list of file attachments. Each attachment should have:
            - filename: Name of the file (required)
            - content: Base64-encoded file content (required if path not provided)
            - mime_type: MIME type (default: application/octet-stream)
            - path: File path to read from (required if content not provided)
    """
    parsed_attachments = _parse_attachments(
        cast(list[AttachmentInput | dict[str, Any]] | None, attachments)
    )

    with create_securemailbox(account) as mailbox:
        mailbox.send_email(
            to=to,
            subject=subject,
            body=body,
            cc=cc,
            reply_to=reply_to,
            attachments=parsed_attachments,
        )
        recipients = ", ".join(to)
        if cc:
            recipients += f" (CC: {', '.join(cc)})"

        msg = f"Email sent successfully to {recipients}"
        if parsed_attachments:
            attachment_names = [a.filename for a in parsed_attachments]
            msg += f" with {len(parsed_attachments)} attachment(s): {', '.join(attachment_names)}"
        return msg
