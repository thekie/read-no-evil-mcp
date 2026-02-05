"""Send email MCP tool."""

import base64
from typing import TypedDict

from read_no_evil_mcp.email.models import OutgoingAttachment
from read_no_evil_mcp.exceptions import PermissionDeniedError
from read_no_evil_mcp.tools._app import mcp
from read_no_evil_mcp.tools._service import create_securemailbox


class AttachmentInput(TypedDict, total=False):
    """Input format for email attachments.

    Either content (base64-encoded) or path must be provided.
    """

    filename: str
    content: str  # base64-encoded bytes
    mime_type: str
    path: str


def _parse_attachments(
    attachment_inputs: list[AttachmentInput] | None,
) -> list[OutgoingAttachment] | None:
    """Convert attachment inputs to OutgoingAttachment objects.

    Args:
        attachment_inputs: List of attachment dictionaries from MCP input.

    Returns:
        List of OutgoingAttachment objects, or None if no attachments.

    Raises:
        ValueError: If attachment is missing required fields.
    """
    if not attachment_inputs:
        return None

    attachments: list[OutgoingAttachment] = []
    for att in attachment_inputs:
        filename = att.get("filename")
        if not filename:
            raise ValueError("Attachment missing required 'filename' field")

        content_b64 = att.get("content")
        path = att.get("path")

        if not content_b64 and not path:
            raise ValueError(f"Attachment '{filename}' must have either 'content' or 'path'")

        content: bytes | None = None
        if content_b64:
            content = base64.b64decode(content_b64)

        attachments.append(
            OutgoingAttachment(
                filename=filename,
                content=content,
                mime_type=att.get("mime_type", "application/octet-stream"),
                path=path,
            )
        )

    return attachments


@mcp.tool
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
    try:
        parsed_attachments = _parse_attachments(attachments)

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
                msg += (
                    f" with {len(parsed_attachments)} attachment(s): {', '.join(attachment_names)}"
                )
            return msg
    except PermissionDeniedError as e:
        return f"Permission denied: {e}"
    except RuntimeError as e:
        return f"Error: {e}"
    except ValueError as e:
        return f"Invalid attachment: {e}"
