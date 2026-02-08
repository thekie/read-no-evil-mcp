"""Pydantic models for MCP tools."""

from pydantic import BaseModel


class AttachmentInput(BaseModel):
    """Input format for email attachments.

    Either content (base64-encoded) or path must be provided.
    """

    filename: str
    content: str | None = None  # base64-encoded bytes
    mime_type: str = "application/octet-stream"
    path: str | None = None
