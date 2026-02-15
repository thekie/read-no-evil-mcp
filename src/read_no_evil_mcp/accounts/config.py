"""Account configuration models with discriminated union for multi-connector support."""

import re
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from read_no_evil_mcp.accounts.permissions import AccountPermissions

# sre_parse was deprecated in 3.11 in favor of re._parser; use whichever is available
_sre_parser: Any = getattr(re, "_parser", None)
if _sre_parser is None:
    import sre_parse as _sre_parser


def _has_nested_quantifiers(pattern: str) -> bool:
    """Check if a regex pattern contains nested quantifiers (ReDoS risk).

    Walks the parsed regex AST looking for a quantifier (MAX_REPEAT/MIN_REPEAT)
    whose body contains another quantifier.
    """
    try:
        parsed = _sre_parser.parse(pattern)
    except re.error:
        return False

    repeat_opcodes = {_sre_parser.MAX_REPEAT, _sre_parser.MIN_REPEAT}

    def _contains_quantifier(items: Any) -> bool:
        for op, av in items:
            if op in repeat_opcodes:
                return True
            if op == _sre_parser.SUBPATTERN and av[3] is not None:
                if _contains_quantifier(av[3]):
                    return True
            if op == _sre_parser.BRANCH:
                for branch in av[1]:
                    if _contains_quantifier(branch):
                        return True
        return False

    def _walk(items: Any) -> bool:
        for op, av in items:
            if op in repeat_opcodes:
                body = av[2]
                if _contains_quantifier(body):
                    return True
            if op == _sre_parser.SUBPATTERN and av[3] is not None:
                if _walk(av[3]):
                    return True
            if op == _sre_parser.BRANCH:
                for branch in av[1]:
                    if _walk(branch):
                        return True
        return False

    return _walk(parsed)


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

    @field_validator("pattern")
    @classmethod
    def validate_pattern(cls, v: str) -> str:
        """Validate that the pattern is a valid regex without ReDoS risk."""
        try:
            re.compile(v)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}") from e
        try:
            nested = _has_nested_quantifiers(v)
        except RecursionError:
            raise ValueError("Regex pattern is too deeply nested.") from None
        if nested:
            raise ValueError(
                "Regex pattern contains nested quantifiers, which risk catastrophic "
                "backtracking (ReDoS). Simplify the pattern to avoid nesting "
                "repetition operators."
            )
        return v


class SubjectRule(BaseModel):
    """Rule for matching email subject lines.

    Attributes:
        pattern: Regex pattern to match against email subject.
        access: Access level to assign when pattern matches.
    """

    pattern: str = Field(..., min_length=1, description="Regex pattern for subject line")
    access: AccessLevel = Field(..., description="Access level when pattern matches")

    @field_validator("pattern")
    @classmethod
    def validate_pattern(cls, v: str) -> str:
        """Validate that the pattern is a valid regex without ReDoS risk."""
        try:
            re.compile(v)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}") from e
        try:
            nested = _has_nested_quantifiers(v)
        except RecursionError:
            raise ValueError("Regex pattern is too deeply nested.") from None
        if nested:
            raise ValueError(
                "Regex pattern contains nested quantifiers, which risk catastrophic "
                "backtracking (ReDoS). Simplify the pattern to avoid nesting "
                "repetition operators."
            )
        return v


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
    sent_folder: str | None = Field(
        default=None,
        description="IMAP folder for saving sent emails (default: auto-detect)",
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
    list_prompts: dict[AccessLevel, str | None] = Field(
        default_factory=dict,
        description="Agent prompts shown in list_emails per access level",
    )
    read_prompts: dict[AccessLevel, str | None] = Field(
        default_factory=dict,
        description="Agent prompts shown in get_email per access level",
    )


# When adding new connector types, convert this to a discriminated union on "type".
AccountConfig = IMAPAccountConfig
