"""Data models for read-no-evil-mcp.

Email-specific models have been moved to email/models.py.
This module re-exports them for backwards compatibility.
"""

from pydantic import BaseModel

# Re-export email models for backwards compatibility
from read_no_evil_mcp.email.models import (
    Attachment,
    Email,
    EmailAddress,
    EmailSummary,
    Folder,
    IMAPConfig,
    SMTPConfig,
)

__all__ = [
    "Attachment",
    "Email",
    "EmailAddress",
    "EmailSummary",
    "Folder",
    "IMAPConfig",
    "ScanResult",
    "SMTPConfig",
]


class ScanResult(BaseModel):
    """Result of scanning content for prompt injection attacks."""

    is_safe: bool
    score: float  # 0.0 = safe, 1.0 = definitely malicious
    detected_patterns: list[str] = []

    @property
    def is_blocked(self) -> bool:
        """Return True if content should be blocked."""
        return not self.is_safe
