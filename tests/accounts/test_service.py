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
    @patch("read_no_evil_mcp.accounts.service.SecureMailbox")
    def test_get_mailbox_creates_correct_config(
        self,
        mock_mailbox: MagicMock,
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
    @patch("read_no_evil_mcp.accounts.service.SecureMailbox")
    def test_get_mailbox_returns_secure_mailbox(
        self,
        mock_mailbox: MagicMock,
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

    @patch("read_no_evil_mcp.accounts.service.IMAPConnector")
    @patch("read_no_evil_mcp.accounts.service.SecureMailbox")
    def test_get_mailbox_passes_permissions(
        self,
        mock_mailbox: MagicMock,
        mock_connector: MagicMock,
    ) -> None:
        """Test get_mailbox passes account permissions to SecureMailbox."""
        from read_no_evil_mcp.accounts.permissions import AccountPermissions

        accounts = [
            AccountConfig(
                id="work",
                host="mail.work.com",
                username="work@example.com",
                permissions=AccountPermissions(read=True, folders=["INBOX"]),
            ),
        ]
        service = AccountService(accounts, MockCredentialBackend({}))

        service.get_mailbox("work")

        # Verify SecureMailbox was called with connector and permissions
        call_args = mock_mailbox.call_args
        assert call_args.args[0] == mock_connector.return_value
        assert call_args.args[1].read is True
        assert call_args.args[1].folders == ["INBOX"]

    @patch("read_no_evil_mcp.accounts.service.IMAPConnector")
    @patch("read_no_evil_mcp.accounts.service.SecureMailbox")
    def test_get_mailbox_creates_smtp_config_when_send_enabled(
        self,
        mock_mailbox: MagicMock,
        mock_connector: MagicMock,
    ) -> None:
        """Test get_mailbox creates SMTP config when send permission is enabled."""
        from read_no_evil_mcp.accounts.permissions import AccountPermissions

        accounts = [
            AccountConfig(
                id="work",
                host="mail.work.com",
                username="work@example.com",
                smtp_host="smtp.work.com",
                smtp_port=587,
                smtp_ssl=False,
                permissions=AccountPermissions(send=True),
            ),
        ]
        credentials = MockCredentialBackend({"work": "secret123"})
        service = AccountService(accounts, credentials)

        service.get_mailbox("work")

        # Verify IMAPConnector was called with smtp_config
        call_args = mock_connector.call_args
        smtp_config = call_args.kwargs.get("smtp_config")
        assert smtp_config is not None
        assert smtp_config.host == "smtp.work.com"
        assert smtp_config.port == 587
        assert smtp_config.username == "work@example.com"
        assert smtp_config.password.get_secret_value() == "secret123"
        assert smtp_config.ssl is False

    @patch("read_no_evil_mcp.accounts.service.IMAPConnector")
    @patch("read_no_evil_mcp.accounts.service.SecureMailbox")
    def test_get_mailbox_no_smtp_config_when_send_disabled(
        self,
        mock_mailbox: MagicMock,
        mock_connector: MagicMock,
    ) -> None:
        """Test get_mailbox does not create SMTP config when send is disabled."""
        from read_no_evil_mcp.accounts.permissions import AccountPermissions

        accounts = [
            AccountConfig(
                id="work",
                host="mail.work.com",
                username="work@example.com",
                permissions=AccountPermissions(send=False),
            ),
        ]
        service = AccountService(accounts, MockCredentialBackend({}))

        service.get_mailbox("work")

        # Verify IMAPConnector was called without smtp_config
        call_args = mock_connector.call_args
        smtp_config = call_args.kwargs.get("smtp_config")
        assert smtp_config is None

    @patch("read_no_evil_mcp.accounts.service.IMAPConnector")
    @patch("read_no_evil_mcp.accounts.service.SecureMailbox")
    def test_get_mailbox_smtp_defaults_to_imap_host(
        self,
        mock_mailbox: MagicMock,
        mock_connector: MagicMock,
    ) -> None:
        """Test SMTP host defaults to IMAP host when not specified."""
        from read_no_evil_mcp.accounts.permissions import AccountPermissions

        accounts = [
            AccountConfig(
                id="work",
                host="mail.work.com",
                username="work@example.com",
                smtp_host=None,  # Not specified, should default to IMAP host
                permissions=AccountPermissions(send=True),
            ),
        ]
        service = AccountService(accounts, MockCredentialBackend({}))

        service.get_mailbox("work")

        # Verify SMTP config uses IMAP host as fallback
        call_args = mock_connector.call_args
        smtp_config = call_args.kwargs.get("smtp_config")
        assert smtp_config is not None
        assert smtp_config.host == "mail.work.com"

    @patch("read_no_evil_mcp.accounts.service.IMAPConnector")
    @patch("read_no_evil_mcp.accounts.service.SecureMailbox")
    def test_get_mailbox_passes_from_address(
        self,
        mock_mailbox: MagicMock,
        mock_connector: MagicMock,
    ) -> None:
        """Test get_mailbox passes from_address to SecureMailbox."""
        accounts = [
            AccountConfig(
                id="work",
                host="mail.work.com",
                username="user",
                from_address="user@example.com",
            ),
        ]
        service = AccountService(accounts, MockCredentialBackend({}))

        service.get_mailbox("work")

        # Verify SecureMailbox was called with from_address
        call_kwargs = mock_mailbox.call_args.kwargs
        assert call_kwargs["from_address"] == "user@example.com"

    @patch("read_no_evil_mcp.accounts.service.IMAPConnector")
    @patch("read_no_evil_mcp.accounts.service.SecureMailbox")
    def test_get_mailbox_passes_from_address_with_name(
        self,
        mock_mailbox: MagicMock,
        mock_connector: MagicMock,
    ) -> None:
        """Test get_mailbox passes from_address and from_name separately."""
        accounts = [
            AccountConfig(
                id="work",
                host="mail.work.com",
                username="user",
                from_address="user@example.com",
                from_name="Atlas",
            ),
        ]
        service = AccountService(accounts, MockCredentialBackend({}))

        service.get_mailbox("work")

        # Verify SecureMailbox was called with separate from_address and from_name
        call_kwargs = mock_mailbox.call_args.kwargs
        assert call_kwargs["from_address"] == "user@example.com"
        assert call_kwargs["from_name"] == "Atlas"

    @patch("read_no_evil_mcp.accounts.service.IMAPConnector")
    @patch("read_no_evil_mcp.accounts.service.SecureMailbox")
    def test_get_mailbox_from_address_falls_back_to_username(
        self,
        mock_mailbox: MagicMock,
        mock_connector: MagicMock,
    ) -> None:
        """Test get_mailbox falls back to username when from_address not configured."""
        accounts = [
            AccountConfig(
                id="work",
                host="mail.work.com",
                username="user@work.com",
            ),
        ]
        service = AccountService(accounts, MockCredentialBackend({}))

        service.get_mailbox("work")

        # Verify SecureMailbox was called with username as from_address
        call_kwargs = mock_mailbox.call_args.kwargs
        assert call_kwargs["from_address"] == "user@work.com"
