"""Connector configuration models."""

from pydantic import BaseModel, SecretStr


class IMAPConfig(BaseModel):
    """IMAP server configuration."""

    host: str
    port: int = 993
    username: str
    password: SecretStr
    ssl: bool = True


class SMTPConfig(BaseModel):
    """SMTP server configuration."""

    host: str
    port: int = 587
    username: str
    password: SecretStr
    ssl: bool = False  # False = use STARTTLS, True = use SSL
