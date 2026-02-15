"""Account permissions model for rights management."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from read_no_evil_mcp.accounts._validators import validate_regex_pattern


class RecipientRule(BaseModel):
    """Rule for matching allowed email recipients.

    Attributes:
        pattern: Regex pattern to match against recipient email address.
    """

    pattern: str = Field(..., min_length=1, description="Regex pattern for recipient email")

    @field_validator("pattern")
    @classmethod
    def validate_pattern(cls, v: str) -> str:
        """Validate that the pattern is a valid regex without ReDoS risk."""
        return validate_regex_pattern(v)


class AccountPermissions(BaseModel):
    """Permissions configuration for an email account.

    Attributes:
        read: Whether reading emails is allowed (default: True).
        delete: Whether deleting emails is allowed (default: False).
        send: Whether sending emails is allowed (default: False).
        move: Whether moving emails between folders is allowed (default: False).
        folders: List of allowed folders, or None for all folders (default: None).
        allowed_recipients: Regex rules restricting who the agent can send to.
            When None or omitted, any recipient is allowed (if send is True).
            When set, every recipient must match at least one pattern.
    """

    read: bool = True
    delete: bool = False
    send: bool = False
    move: bool = False
    folders: list[str] | None = None
    allowed_recipients: list[RecipientRule] | None = None
