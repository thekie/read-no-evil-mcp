"""Account configuration models with discriminated union for multi-connector support."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from read_no_evil_mcp.accounts.permissions import AccountPermissions


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
    """

    pattern: str = Field(..., min_length=1, description="Regex pattern for sender email")
    access: AccessLevel = Field(..., description="Access level when pattern matches")


class SubjectRule(BaseModel):
    """Rule for matching email subject lines.

    Attributes:
        pattern: Regex pattern to match against email subject.
        access: Access level to assign when pattern matches.
    """

    pattern: str = Field(..., min_length=1, description="Regex pattern for subject line")
    access: AccessLevel = Field(..., description="Access level when pattern matches")


class BaseAccountConfig(BaseModel):
    """Base configuration shared by all account types.

    Attributes:
        id: Unique identifier for the account (e.g., "work", "personal").
    """

    id: str = Field(
        ...,
        min_length=1,
        pattern=r"^[a-zA-Z][a-zA-Z0-9_-]*$",
        description="Unique account identifier (alphanumeric, hyphens, underscores)",
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

    # Access rules
    sender_rules: list[SenderRule] = Field(
        default_factory=list,
        description="Rules for matching sender email addresses",
    )
    subject_rules: list[SubjectRule] = Field(
        default_factory=list,
        description="Rules for matching email subject lines",
    )
    list_prompts: dict[str, str | None] = Field(
        default_factory=dict,
        description="Agent prompts shown in list_emails per access level",
    )
    read_prompts: dict[str, str | None] = Field(
        default_factory=dict,
        description="Agent prompts shown in get_email per access level",
    )


# Future connectors will follow the same pattern as IMAPAccountConfig:
# - Inherit from BaseAccountConfig
# - Add a `type` field with Literal["connector_name"]
# - Add connector-specific fields
# Examples: GmailAccountConfig (type="gmail"), MSGraphAccountConfig (type="msgraph")

# Discriminated union - Pydantic picks the right type based on "type" field.
# When adding new connectors, convert AccountConfig to a discriminated union:
#
#     from typing import Annotated, Union
#     AccountConfig = Annotated[
#         Union[IMAPAccountConfig, GmailAccountConfig, MSGraphAccountConfig],
#         Field(discriminator="type"),
#     ]
#
# For now with single type, use simple alias (discriminator activates with Union).
AccountConfig = IMAPAccountConfig
