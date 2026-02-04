"""Tests for AccountConfig model."""

import pytest
from pydantic import ValidationError

from read_no_evil_mcp.accounts.config import AccountConfig


class TestAccountConfig:
    def test_valid_config(self) -> None:
        """Test valid account configuration."""
        config = AccountConfig(
            id="work",
            type="imap",
            host="mail.example.com",
            username="user@example.com",
        )
        assert config.id == "work"
        assert config.type == "imap"
        assert config.host == "mail.example.com"
        assert config.port == 993  # default
        assert config.ssl is True  # default

    def test_custom_port(self) -> None:
        """Test account configuration with custom port."""
        config = AccountConfig(
            id="work",
            host="mail.example.com",
            port=143,
            username="user@example.com",
            ssl=False,
        )
        assert config.port == 143
        assert config.ssl is False

    def test_id_validation_starts_with_letter(self) -> None:
        """Test that ID must start with a letter."""
        with pytest.raises(ValidationError) as exc_info:
            AccountConfig(
                id="123invalid",
                host="mail.example.com",
                username="user@example.com",
            )
        assert "pattern" in str(exc_info.value).lower()

    def test_id_validation_allows_hyphens_underscores(self) -> None:
        """Test that ID allows hyphens and underscores."""
        config = AccountConfig(
            id="my-work_email",
            host="mail.example.com",
            username="user@example.com",
        )
        assert config.id == "my-work_email"

    def test_id_validation_empty(self) -> None:
        """Test that ID cannot be empty."""
        with pytest.raises(ValidationError):
            AccountConfig(
                id="",
                host="mail.example.com",
                username="user@example.com",
            )

    def test_host_required(self) -> None:
        """Test that host is required."""
        with pytest.raises(ValidationError):
            AccountConfig(
                id="work",
                username="user@example.com",
            )  # type: ignore[call-arg]

    def test_username_required(self) -> None:
        """Test that username is required."""
        with pytest.raises(ValidationError):
            AccountConfig(
                id="work",
                host="mail.example.com",
            )  # type: ignore[call-arg]

    def test_port_validation(self) -> None:
        """Test port validation (1-65535)."""
        with pytest.raises(ValidationError):
            AccountConfig(
                id="work",
                host="mail.example.com",
                port=0,
                username="user@example.com",
            )

        with pytest.raises(ValidationError):
            AccountConfig(
                id="work",
                host="mail.example.com",
                port=70000,
                username="user@example.com",
            )
