"""A secure email gateway MCP server that protects AI agents from prompt injection attacks in emails."""

from read_no_evil_mcp.config import Settings
from read_no_evil_mcp.email.connectors.base import BaseConnector
from read_no_evil_mcp.email.connectors.imap import IMAPConnector
from read_no_evil_mcp.mailbox import PromptInjectionError, SecureMailbox
from read_no_evil_mcp.models import (
    Attachment,
    Email,
    EmailAddress,
    EmailSummary,
    Folder,
    IMAPConfig,
    ScanResult,
)
from read_no_evil_mcp.protection.heuristic import HeuristicScanner
from read_no_evil_mcp.protection.service import ProtectionService

__version__ = "0.1.0"

__all__ = [
    "Attachment",
    "BaseConnector",
    "Email",
    "EmailAddress",
    "EmailSummary",
    "Folder",
    "HeuristicScanner",
    "IMAPConfig",
    "IMAPConnector",
    "PromptInjectionError",
    "ProtectionService",
    "ScanResult",
    "SecureMailbox",
    "Settings",
]
