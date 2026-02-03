"""Email service and connectors for read-no-evil-mcp."""

from read_no_evil_mcp.email.connectors.base import BaseConnector
from read_no_evil_mcp.email.connectors.imap import IMAPConnector
from read_no_evil_mcp.email.service import EmailService

__all__ = ["BaseConnector", "EmailService", "IMAPConnector"]
