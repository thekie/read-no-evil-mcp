"""Account configuration models with discriminated union for multi-connector support."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from read_no_evil_mcp.accounts._validators import validate_regex_pattern
from read_no_evil_mcp.accounts.permissions import AccountPermissions
from read_no_evil_mcp.protection.models import ProtectionConfig


class AccessLevel(str, Enum):
    """Access level for email based on sender/subject rules.

    Levels are ordered by restrictiveness: hide > ask_before_read > show > trusted.
    When multiple rules match, the most restrictive level wins.
    """

    TRUSTED = "trusted"
    SHOW = "show"
    ASK_BEFORE_READ = "ask_before_read"
    HIDE = "hide"


# Restrictiveness order (higher index = more restrictive)
ACCESS_LEVEL_RESTRICTIVENESS: dict[AccessLevel, int] = {
    AccessLevel.TRUSTED: 0,
    AccessLevel.SHOW: 1,
    AccessLevel.ASK_BEFORE_READ: 2,
    AccessLevel.HIDE: 3,
}


class SenderRule(BaseModel):
    """Rule for matching email sender addresses.

    Attributes:
        pattern: Regex pattern to match against sender email address.
        access: Access level to assign when pattern matches.
        skip_protection: If True, skip prompt injection scanning for matching emails.
    """

    pattern: str = Field(..., min_length=1, description="Regex pattern for sender email")
    access: AccessLevel = Field(..., description="Access level when pattern matches")
    skip_protection: bool = Field(
        default=False,
        description="Skip prompt injection scanning for matching emails",
    )

    @field_validator("pattern")
    @classmethod
    def validate_pattern(cls, v: str) -> str:
        """Validate that the pattern is a valid regex without ReDoS risk."""
        return validate_regex_pattern(v)


class SubjectRule(BaseModel):
    """Rule for matching email subject lines.

    Attributes:
        pattern: Regex pattern to match against email subject.
        access: Access level to assign when pattern matches.
        skip_protection: If True, skip prompt injection scanning for matching emails.
    """

    pattern: str = Field(..., min_length=1, description="Regex pattern for subject line")
    access: AccessLevel = Field(..., description="Access level when pattern matches")
    skip_protection: bool = Field(
        default=False,
        description="Skip prompt injection scanning for matching emails",
    )

    @field_validator("pattern")
    @classmethod
    def validate_pattern(cls, v: str) -> str:
        """Validate that the pattern is a valid regex without ReDoS risk."""
        return validate_regex_pattern(v)


class BaseAccountConfig(BaseModel):
    """Base configuration shared by all account types.

    Attributes:
        id: Unique identifier for the account (e.g., "work", "personal").
    """

    id: str = Field(
        ...,
        min_length=1,
        pattern=r"^[a-zA-Z][a-zA-Z0-9@._-]*$",
        description="Unique account identifier (alphanumeric, hyphens, underscores, or email address)",
    )


class IMAPAccountConfig(BaseAccountConfig):
    """IMAP-specific account configuration.

    Attributes:
        type: Connector type, always "imap" for this class.
        host: Email server hostname.
        port: Email server port (default: 993 for IMAP SSL).
        username: Account username/email address.
        ssl: Whether to use SSL/TLS (default: True).
        permissions: Account permissions (default: read-only).
        smtp_host: SMTP server hostname (default: same as IMAP host).
        smtp_port: SMTP server port (default: 587 for STARTTLS).
        smtp_ssl: Use SSL instead of STARTTLS for SMTP (default: False).
    """

    type: Literal["imap"] = Field(
        default="imap",
        description="Connector type (imap)",
    )
    host: str = Field(..., min_length=1, description="Email server hostname")
    port: int = Field(default=993, ge=1, le=65535, description="Email server port")
    username: str = Field(..., min_length=1, description="Account username/email")
    ssl: bool = Field(default=True, description="Use SSL/TLS connection")
    permissions: AccountPermissions = Field(
        default_factory=AccountPermissions,
        description="Account permissions (default: read-only)",
    )
    smtp_host: str | None = Field(
        default=None,
        description="SMTP server hostname (defaults to IMAP host)",
    )
    smtp_port: int = Field(
        default=587,
        ge=1,
        le=65535,
        description="SMTP server port (default: 587 for STARTTLS)",
    )
    smtp_ssl: bool = Field(
        default=False,
        description="Use SSL instead of STARTTLS for SMTP (default: False)",
    )
    from_address: str | None = Field(
        default=None,
        min_length=1,
        description="Sender email address for outgoing emails (required for send)",
    )
    from_name: str | None = Field(
        default=None,
        description="Display name for outgoing emails (e.g., 'Atlas')",
    )
    sent_folder: str | None = Field(
        default="Sent",
        description="IMAP folder to save sent emails to (e.g., 'Sent', '[Gmail]/Sent Mail'). "
        "Set to null to disable saving sent emails.",
    )

    # Protection settings (overrides global threshold)
    protection: ProtectionConfig | None = Field(
        default=None,
        description="Per-account protection settings (overrides global threshold)",
    )

    # Access rules
    sender_rules: list[SenderRule] = Field(
        default_factory=list,
        description="Rules for matching sender email addresses",
    )
    subject_rules: list[SubjectRule] = Field(
        default_factory=list,
        description="Rules for matching email subject lines",
    )
    list_prompts: dict[AccessLevel, str | None] = Field(
        default_factory=dict,
        description="Agent prompts shown in list_emails per access level",
    )
    read_prompts: dict[AccessLevel, str | None] = Field(
        default_factory=dict,
        description="Agent prompts shown in get_email per access level",
    )
    unscanned_list_prompt: str | None = Field(
        default=None,
        description="Agent prompt shown in list_emails for unscanned emails (skip_protection)",
    )
    unscanned_read_prompt: str | None = Field(
        default=None,
        description="Agent prompt shown in get_email for unscanned emails (skip_protection)",
    )


# When adding new connector types, convert this to a discriminated union on "type".
AccountConfig = IMAPAccountConfig
