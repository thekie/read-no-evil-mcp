"""Pydantic models for MCP tools."""

import base64

from pydantic import BaseModel, field_validator

__all__ = ["AttachmentInput"]


class AttachmentInput(BaseModel):
    """Input format for email attachments.

    Either content (base64-encoded) or path must be provided.
    """

    filename: str
    content: str | None = None  # base64-encoded bytes
    mime_type: str = "application/octet-stream"
    path: str | None = None

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        if not v:
            raise ValueError("filename must not be empty")
        if "/" in v or "\\" in v:
            raise ValueError("filename must not contain path separators")
        if v.startswith("."):
            raise ValueError("filename must not start with '.'")
        return v

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str | None) -> str | None:
        if v is not None:
            try:
                base64.b64decode(v)
            except Exception as err:
                raise ValueError("content must be valid base64") from err
        return v
