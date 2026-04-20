"""Email connectors for read-no-evil-mcp."""

from read_no_evil_mcp.email.connectors.base import BaseConnector
from read_no_evil_mcp.email.connectors.config import GmailConfig, IMAPConfig, SMTPConfig
from read_no_evil_mcp.email.connectors.gmail import GmailConnector
from read_no_evil_mcp.email.connectors.imap import IMAPConnector

__all__ = [
    "BaseConnector",
    "GmailConfig",
    "GmailConnector",
    "IMAPConfig",
    "IMAPConnector",
    "SMTPConfig",
]
