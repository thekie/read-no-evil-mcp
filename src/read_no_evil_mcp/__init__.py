"""A secure email gateway MCP server that protects AI agents from prompt injection attacks in emails."""

from read_no_evil_mcp.models import (
    Attachment,
    Email,
    EmailAddress,
    EmailSummary,
    Folder,
    IMAPConfig,
)

__version__ = "0.1.0"

__all__ = [
    "Attachment",
    "Email",
    "EmailAddress",
    "EmailSummary",
    "Folder",
    "IMAPConfig",
]
