"""A secure email gateway MCP server that protects AI agents from prompt injection attacks in emails."""

from read_no_evil_mcp.config import Settings
from read_no_evil_mcp.connectors.base import BaseConnector
from read_no_evil_mcp.connectors.imap import IMAPConnector
from read_no_evil_mcp.models import (
    Attachment,
    Email,
    EmailAddress,
    EmailSummary,
    Folder,
    IMAPConfig,
)
from read_no_evil_mcp.service import EmailService

__version__ = "0.1.0"

__all__ = [
    "Attachment",
    "BaseConnector",
    "Email",
    "EmailAddress",
    "EmailService",
    "EmailSummary",
    "Folder",
    "IMAPConfig",
    "IMAPConnector",
    "Settings",
]
