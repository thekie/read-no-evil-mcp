"""Email data models."""

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, model_validator


class EmailAddress(BaseModel):
    """Parsed email address with optional display name."""

    name: str | None = None
    address: str

    def __str__(self) -> str:
        if self.name:
            return f"{self.name} <{self.address}>"
        return self.address


class Folder(BaseModel):
    """IMAP folder/mailbox."""

    name: str
    delimiter: str = "/"
    flags: list[str] = []


class Attachment(BaseModel):
    """Email attachment metadata (content not included)."""

    filename: str
    content_type: str
    size: int | None = None


class OutgoingAttachment(BaseModel):
    """Attachment for outgoing emails.

    Supports two modes:
    - In-memory: Provide content bytes directly
    - File-based: Provide path to read from (content will be loaded)

    At least one of content or path must be provided.
    """

    filename: str
    content: bytes | None = None
    mime_type: str = "application/octet-stream"
    path: str | None = None

    @model_validator(mode="after")
    def _require_content_or_path(self) -> "OutgoingAttachment":
        if self.content is None and self.path is None:
            raise ValueError("Either content or path must be provided")
        return self

    def check_size(self, max_size: int) -> None:
        """Check attachment size without reading file content.

        Raises:
            ValueError: If attachment exceeds max_size.
            FileNotFoundError: If path doesn't exist.
        """
        if self.content is not None:
            size = len(self.content)
        else:
            assert self.path is not None
            size = Path(self.path).stat().st_size
        if size > max_size:
            raise ValueError(f"Attachment too large: {size} bytes (max {max_size})")

    def get_content(self) -> bytes:
        """Get attachment content, loading from path if needed.

        Returns:
            The attachment content as bytes.

        Raises:
            FileNotFoundError: If path is provided but file doesn't exist.
        """
        if self.content is not None:
            return self.content
        assert self.path is not None
        with open(self.path, "rb") as f:
            return f.read()


class EmailSummary(BaseModel):
    """Lightweight email representation for list views."""

    uid: int
    folder: str
    subject: str
    sender: EmailAddress
    date: datetime
    has_attachments: bool = False
    is_seen: bool = False


class Email(EmailSummary):
    """Full email content."""

    to: list[EmailAddress] = []
    cc: list[EmailAddress] = []
    body_plain: str | None = None
    body_html: str | None = None
    attachments: list[Attachment] = []
    message_id: str | None = None
