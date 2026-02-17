"""Data models for read-no-evil-mcp.

This module contains the secure mailbox wrapper models and re-exports
other models for backwards compatibility.
"""

from dataclasses import dataclass

from read_no_evil_mcp.accounts.config import AccessLevel

# Re-export for backwards compatibility
from read_no_evil_mcp.email.connectors.config import IMAPConfig, SMTPConfig
from read_no_evil_mcp.email.models import (
    Attachment,
    Email,
    EmailAddress,
    EmailSummary,
    Folder,
    OutgoingAttachment,
)
from read_no_evil_mcp.protection.models import ScanResult

__all__ = [
    # Secure mailbox models (primary)
    "FetchResult",
    "SecureEmail",
    "SecureEmailSummary",
    # Re-exports for backwards compatibility
    "Attachment",
    "Email",
    "EmailAddress",
    "EmailSummary",
    "Folder",
    "IMAPConfig",
    "OutgoingAttachment",
    "ScanResult",
    "SMTPConfig",
]


@dataclass
class FetchResult:
    """Paginated result from fetching email summaries."""

    items: list["SecureEmailSummary"]
    total: int
    blocked_count: int = 0
    hidden_count: int = 0


@dataclass
class SecureEmailSummary:
    """Email summary enriched with security context.

    Wraps an EmailSummary with access level and prompt information
    determined by the account's access rules.
    """

    summary: EmailSummary
    access_level: AccessLevel
    prompt: str | None = None
    protection_skipped: bool = False


@dataclass
class SecureEmail:
    """Full email enriched with security context.

    Wraps an Email with access level and prompt information
    determined by the account's access rules.
    """

    email: Email
    access_level: AccessLevel
    prompt: str | None = None
    protection_skipped: bool = False
