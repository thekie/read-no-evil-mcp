"""Email connectors for read-no-evil-mcp."""

from read_no_evil_mcp.email.connectors.base import BaseConnector
from read_no_evil_mcp.email.connectors.config import IMAPConfig, SMTPConfig
from read_no_evil_mcp.email.connectors.imap import IMAPConnector

__all__ = ["BaseConnector", "IMAPConfig", "IMAPConnector", "SMTPConfig"]
