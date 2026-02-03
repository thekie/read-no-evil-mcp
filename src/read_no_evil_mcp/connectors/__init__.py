"""Email connectors for read-no-evil-mcp."""

from read_no_evil_mcp.connectors.base import BaseConnector
from read_no_evil_mcp.connectors.imap import IMAPConnector

__all__ = ["BaseConnector", "IMAPConnector"]
