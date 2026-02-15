"""Tests for AccountPermissions."""

import pytest
from pydantic import ValidationError

from read_no_evil_mcp.accounts.permissions import AccountPermissions, RecipientRule


class TestAccountPermissions:
    def test_default_permissions(self) -> None:
        """Test default permissions are read-only."""
        permissions = AccountPermissions()

        assert permissions.read is True
        assert permissions.delete is False
        assert permissions.send is False
        assert permissions.move is False
        assert permissions.folders is None
        assert permissions.allowed_recipients is None

    def test_explicit_permissions(self) -> None:
        """Test explicit permission settings."""
        permissions = AccountPermissions(
            read=True,
            delete=True,
            send=True,
            move=True,
            folders=["INBOX", "Sent"],
        )

        assert permissions.read is True
        assert permissions.delete is True
        assert permissions.send is True
        assert permissions.move is True
        assert permissions.folders == ["INBOX", "Sent"]

    def test_read_only_permissions(self) -> None:
        """Test read-only with folder restriction."""
        permissions = AccountPermissions(
            folders=["INBOX"],
        )

        assert permissions.read is True
        assert permissions.delete is False
        assert permissions.folders == ["INBOX"]

    def test_no_read_permissions(self) -> None:
        """Test that read can be explicitly disabled."""
        permissions = AccountPermissions(read=False)

        assert permissions.read is False

    def test_allowed_recipients_with_rules(self) -> None:
        """Test allowed_recipients with configured rules."""
        permissions = AccountPermissions(
            send=True,
            allowed_recipients=[
                RecipientRule(pattern=r"^team@example\.com$"),
                RecipientRule(pattern=r"@corp\.com$"),
            ],
        )

        assert permissions.allowed_recipients is not None
        assert len(permissions.allowed_recipients) == 2
        assert permissions.allowed_recipients[0].pattern == r"^team@example\.com$"
        assert permissions.allowed_recipients[1].pattern == r"@corp\.com$"

    def test_allowed_recipients_none_by_default(self) -> None:
        """Test that allowed_recipients defaults to None (no restriction)."""
        permissions = AccountPermissions(send=True)

        assert permissions.allowed_recipients is None


class TestRecipientRule:
    def test_valid_exact_address_pattern(self) -> None:
        rule = RecipientRule(pattern=r"^user@example\.com$")
        assert rule.pattern == r"^user@example\.com$"

    def test_valid_domain_pattern(self) -> None:
        rule = RecipientRule(pattern=r"@example\.com$")
        assert rule.pattern == r"@example\.com$"

    def test_valid_wildcard_pattern(self) -> None:
        rule = RecipientRule(pattern=r".*")
        assert rule.pattern == ".*"

    def test_rejects_nested_quantifier_pattern(self) -> None:
        with pytest.raises(ValidationError, match="nested quantifiers"):
            RecipientRule(pattern=r"(a+)+$")

    def test_rejects_invalid_regex(self) -> None:
        with pytest.raises(ValidationError, match="Invalid regex pattern"):
            RecipientRule(pattern=r"[invalid")

    def test_rejects_empty_pattern(self) -> None:
        with pytest.raises(ValidationError):
            RecipientRule(pattern="")
