"""Data models for read-no-evil-mcp."""

from datetime import datetime

from pydantic import BaseModel, SecretStr


class IMAPConfig(BaseModel):
    """IMAP server configuration."""

    host: str
    port: int = 993
    username: str
    password: SecretStr
    ssl: bool = True


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


class EmailSummary(BaseModel):
    """Lightweight email representation for list views."""

    uid: int
    folder: str
    subject: str
    sender: EmailAddress
    date: datetime
    has_attachments: bool = False


class Email(EmailSummary):
    """Full email content."""

    to: list[EmailAddress] = []
    cc: list[EmailAddress] = []
    body_plain: str | None = None
    body_html: str | None = None
    attachments: list[Attachment] = []
    message_id: str | None = None
