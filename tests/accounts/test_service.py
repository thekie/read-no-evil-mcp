"""Tests for AccountService."""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from read_no_evil_mcp.accounts.config import AccountConfig
from read_no_evil_mcp.accounts.credentials.base import CredentialBackend
from read_no_evil_mcp.accounts.service import AccountService
from read_no_evil_mcp.exceptions import AccountNotFoundError


class MockCredentialBackend(CredentialBackend):
    """Mock credential backend for testing."""

    def __init__(self, passwords: dict[str, str]) -> None:
        self._passwords = passwords

    def get_password(self, account_id: str) -> SecretStr:
        return SecretStr(self._passwords.get(account_id, "mock-password"))


class TestAccountService:
    def test_list_accounts(self) -> None:
        """Test listing account IDs."""
        accounts = [
            AccountConfig(id="work", host="mail.work.com", username="work@example.com"),
            AccountConfig(id="personal", host="mail.personal.com", username="personal@example.com"),
        ]
        service = AccountService(accounts, MockCredentialBackend({}))

        result = service.list_accounts()

        assert result == ["work", "personal"]

    def test_list_accounts_empty(self) -> None:
        """Test listing accounts when none configured."""
        service = AccountService([], MockCredentialBackend({}))

        result = service.list_accounts()

        assert result == []

    def test_get_mailbox_account_not_found(self) -> None:
        """Test get_mailbox raises AccountNotFoundError."""
        accounts = [
            AccountConfig(id="work", host="mail.work.com", username="work@example.com"),
        ]
        service = AccountService(accounts, MockCredentialBackend({}))

        with pytest.raises(AccountNotFoundError) as exc_info:
            service.get_mailbox("nonexistent")

        assert exc_info.value.account_id == "nonexistent"

    @patch("read_no_evil_mcp.accounts.service.IMAPConnector")
    @patch("read_no_evil_mcp.accounts.service.EmailService")
    @patch("read_no_evil_mcp.accounts.service.SecureMailbox")
    def test_get_mailbox_creates_correct_config(
        self,
        mock_mailbox: MagicMock,
        mock_email_service: MagicMock,
        mock_connector: MagicMock,
    ) -> None:
        """Test get_mailbox creates connector with correct config."""
        accounts = [
            AccountConfig(
                id="work",
                host="mail.work.com",
                port=993,
                username="work@example.com",
                ssl=True,
            ),
        ]
        credentials = MockCredentialBackend({"work": "secret123"})
        service = AccountService(accounts, credentials)

        service.get_mailbox("work")

        # Verify IMAPConfig was created with correct values
        call_args = mock_connector.call_args
        imap_config = call_args.args[0]
        assert imap_config.host == "mail.work.com"
        assert imap_config.port == 993
        assert imap_config.username == "work@example.com"
        assert imap_config.password.get_secret_value() == "secret123"
        assert imap_config.ssl is True

    @patch("read_no_evil_mcp.accounts.service.IMAPConnector")
    @patch("read_no_evil_mcp.accounts.service.EmailService")
    @patch("read_no_evil_mcp.accounts.service.SecureMailbox")
    def test_get_mailbox_returns_secure_mailbox(
        self,
        mock_mailbox: MagicMock,
        mock_email_service: MagicMock,
        mock_connector: MagicMock,
    ) -> None:
        """Test get_mailbox returns SecureMailbox instance."""
        accounts = [
            AccountConfig(id="work", host="mail.work.com", username="work@example.com"),
        ]
        service = AccountService(accounts, MockCredentialBackend({}))

        result = service.get_mailbox("work")

        mock_mailbox.assert_called_once()
        assert result == mock_mailbox.return_value
