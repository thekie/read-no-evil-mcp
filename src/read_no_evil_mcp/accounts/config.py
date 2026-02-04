"""Account configuration model."""

from typing import Literal

from pydantic import BaseModel, Field


class AccountConfig(BaseModel):
    """Configuration for a single email account.

    Attributes:
        id: Unique identifier for the account (e.g., "work", "personal").
        type: Connector type. Currently only "imap" is supported.
        host: Email server hostname.
        port: Email server port (default: 993 for IMAP SSL).
        username: Account username/email address.
        ssl: Whether to use SSL/TLS (default: True).
    """

    id: str = Field(
        ...,
        min_length=1,
        pattern=r"^[a-zA-Z][a-zA-Z0-9_-]*$",
        description="Unique account identifier (alphanumeric, hyphens, underscores)",
    )
    type: Literal["imap"] = Field(
        default="imap",
        description="Connector type (currently only 'imap' supported)",
    )
    host: str = Field(..., min_length=1, description="Email server hostname")
    port: int = Field(default=993, ge=1, le=65535, description="Email server port")
    username: str = Field(..., min_length=1, description="Account username/email")
    ssl: bool = Field(default=True, description="Use SSL/TLS connection")
