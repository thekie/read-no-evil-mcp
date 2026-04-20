"""Email connectors and models for read-no-evil-mcp."""

from read_no_evil_mcp.email.connectors.base import BaseConnector
from read_no_evil_mcp.email.connectors.config import GmailConfig, IMAPConfig, SMTPConfig
from read_no_evil_mcp.email.connectors.gmail import GmailConnector
from read_no_evil_mcp.email.connectors.imap import IMAPConnector
from read_no_evil_mcp.email.models import (
    Attachment,
    Email,
    EmailAddress,
    EmailSummary,
    Folder,
)

__all__ = [
    "Attachment",
    "BaseConnector",
    "Email",
    "EmailAddress",
    "EmailSummary",
    "Folder",
    "GmailConfig",
    "GmailConnector",
    "IMAPConfig",
    "IMAPConnector",
    "SMTPConfig",
]
