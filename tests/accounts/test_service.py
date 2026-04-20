"""Tests for AccountService."""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from read_no_evil_mcp.accounts.config import GmailAccountConfig, IMAPAccountConfig
from read_no_evil_mcp.accounts.credentials.base import CredentialBackend
from read_no_evil_mcp.accounts.service import AccountService
from read_no_evil_mcp.exceptions import AccountNotFoundError
from read_no_evil_mcp.protection.models import ProtectionConfig


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
            IMAPAccountConfig(id="work", host="mail.work.com", username="work@example.com"),
            IMAPAccountConfig(
                id="personal", host="mail.personal.com", username="personal@example.com"
            ),
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
            IMAPAccountConfig(id="work", host="mail.work.com", username="work@example.com"),
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
            IMAPAccountConfig(
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
            IMAPAccountConfig(id="work", host="mail.work.com", username="work@example.com"),
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
            IMAPAccountConfig(
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
            IMAPAccountConfig(
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
            IMAPAccountConfig(
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
            IMAPAccountConfig(
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
            IMAPAccountConfig(
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
            IMAPAccountConfig(
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
            IMAPAccountConfig(
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

    @patch("read_no_evil_mcp.accounts.service.IMAPConnector")
    @patch("read_no_evil_mcp.accounts.service.SecureMailbox")
    def test_get_mailbox_passes_sent_folder(
        self,
        mock_mailbox: MagicMock,
        mock_connector: MagicMock,
    ) -> None:
        """Test get_mailbox passes sent_folder via IMAPConfig."""
        accounts = [
            IMAPAccountConfig(
                id="work",
                host="mail.work.com",
                username="work@example.com",
                sent_folder="[Gmail]/Sent Mail",
            ),
        ]
        service = AccountService(accounts, MockCredentialBackend({}))

        service.get_mailbox("work")

        imap_config = mock_connector.call_args.args[0]
        assert imap_config.sent_folder == "[Gmail]/Sent Mail"

    @patch("read_no_evil_mcp.accounts.service.IMAPConnector")
    @patch("read_no_evil_mcp.accounts.service.SecureMailbox")
    def test_get_mailbox_passes_sent_folder_none(
        self,
        mock_mailbox: MagicMock,
        mock_connector: MagicMock,
    ) -> None:
        """Test get_mailbox passes None sent_folder via IMAPConfig to disable saving."""
        accounts = [
            IMAPAccountConfig(
                id="work",
                host="mail.work.com",
                username="work@example.com",
                sent_folder=None,
            ),
        ]
        service = AccountService(accounts, MockCredentialBackend({}))

        service.get_mailbox("work")

        imap_config = mock_connector.call_args.args[0]
        assert imap_config.sent_folder is None

    @patch("read_no_evil_mcp.accounts.service.IMAPConnector")
    @patch("read_no_evil_mcp.accounts.service.SecureMailbox")
    def test_get_mailbox_uses_global_default_threshold(
        self,
        mock_mailbox: MagicMock,
        mock_connector: MagicMock,
    ) -> None:
        """Test get_mailbox uses global default threshold when no per-account override."""
        accounts = [
            IMAPAccountConfig(
                id="work",
                host="mail.work.com",
                username="work@example.com",
            ),
        ]
        service = AccountService(accounts, MockCredentialBackend({}), default_threshold=0.7)

        service.get_mailbox("work")

        # Verify SecureMailbox was called with a protection service
        call_kwargs = mock_mailbox.call_args.kwargs
        protection = call_kwargs["protection"]
        assert protection._scanner._threshold == 0.7

    @patch("read_no_evil_mcp.accounts.service.IMAPConnector")
    @patch("read_no_evil_mcp.accounts.service.SecureMailbox")
    def test_get_mailbox_uses_per_account_threshold_override(
        self,
        mock_mailbox: MagicMock,
        mock_connector: MagicMock,
    ) -> None:
        """Test get_mailbox uses per-account threshold when configured."""
        accounts = [
            IMAPAccountConfig(
                id="work",
                host="mail.work.com",
                username="work@example.com",
                protection=ProtectionConfig(threshold=0.9),
            ),
        ]
        service = AccountService(accounts, MockCredentialBackend({}), default_threshold=0.5)

        service.get_mailbox("work")

        # Verify the per-account threshold (0.9) overrides the global default (0.5)
        call_kwargs = mock_mailbox.call_args.kwargs
        protection = call_kwargs["protection"]
        assert protection._scanner._threshold == 0.9

    @patch("read_no_evil_mcp.accounts.service.IMAPConnector")
    @patch("read_no_evil_mcp.accounts.service.SecureMailbox")
    def test_get_mailbox_passes_protection_to_secure_mailbox(
        self,
        mock_mailbox: MagicMock,
        mock_connector: MagicMock,
    ) -> None:
        """Test get_mailbox passes ProtectionService to SecureMailbox."""
        from read_no_evil_mcp.protection.service import ProtectionService

        accounts = [
            IMAPAccountConfig(
                id="work",
                host="mail.work.com",
                username="work@example.com",
            ),
        ]
        service = AccountService(accounts, MockCredentialBackend({}))

        service.get_mailbox("work")

        call_kwargs = mock_mailbox.call_args.kwargs
        assert isinstance(call_kwargs["protection"], ProtectionService)


class TestAccountServiceGmail:
    """Tests for AccountService with Gmail connector."""

    @patch("read_no_evil_mcp.accounts.service.GmailConnector")
    @patch("read_no_evil_mcp.accounts.service.SecureMailbox")
    def test_get_mailbox_creates_gmail_connector(
        self,
        mock_mailbox: MagicMock,
        mock_gmail_connector: MagicMock,
    ) -> None:
        """Test get_mailbox creates GmailConnector with correct config."""
        accounts = [
            GmailAccountConfig(
                id="gmail-work",
                email="user@gmail.com",
                credentials_file="/path/to/creds.json",
                token_file="/path/to/token.json",
            ),
        ]
        service = AccountService(accounts, MockCredentialBackend({}))

        service.get_mailbox("gmail-work")

        call_args = mock_gmail_connector.call_args
        gmail_config = call_args.args[0]
        assert gmail_config.credentials_file == "/path/to/creds.json"
        assert gmail_config.token_file == "/path/to/token.json"

    @patch("read_no_evil_mcp.accounts.service.GmailConnector")
    @patch("read_no_evil_mcp.accounts.service.SecureMailbox")
    def test_get_mailbox_gmail_no_password_retrieval(
        self,
        mock_mailbox: MagicMock,
        mock_gmail_connector: MagicMock,
    ) -> None:
        """Test get_mailbox does NOT call credential backend for Gmail accounts."""
        accounts = [
            GmailAccountConfig(
                id="gmail-work",
                email="user@gmail.com",
                credentials_file="/path/to/creds.json",
            ),
        ]
        mock_backend = MagicMock(spec=CredentialBackend)
        service = AccountService(accounts, mock_backend)

        service.get_mailbox("gmail-work")

        mock_backend.get_password.assert_not_called()

    @patch("read_no_evil_mcp.accounts.service.GmailConnector")
    @patch("read_no_evil_mcp.accounts.service.SecureMailbox")
    def test_get_mailbox_gmail_from_address_defaults_to_email(
        self,
        mock_mailbox: MagicMock,
        mock_gmail_connector: MagicMock,
    ) -> None:
        """Test get_mailbox falls back to email field when from_address not set."""
        accounts = [
            GmailAccountConfig(
                id="gmail-work",
                email="user@gmail.com",
                credentials_file="/path/to/creds.json",
            ),
        ]
        service = AccountService(accounts, MockCredentialBackend({}))

        service.get_mailbox("gmail-work")

        call_kwargs = mock_mailbox.call_args.kwargs
        assert call_kwargs["from_address"] == "user@gmail.com"

    @patch("read_no_evil_mcp.accounts.service.GmailConnector")
    @patch("read_no_evil_mcp.accounts.service.SecureMailbox")
    def test_get_mailbox_gmail_with_custom_from_address(
        self,
        mock_mailbox: MagicMock,
        mock_gmail_connector: MagicMock,
    ) -> None:
        """Test get_mailbox uses custom from_address when set."""
        accounts = [
            GmailAccountConfig(
                id="gmail-work",
                email="user@gmail.com",
                credentials_file="/path/to/creds.json",
                from_address="alias@gmail.com",
                from_name="Atlas",
            ),
        ]
        service = AccountService(accounts, MockCredentialBackend({}))

        service.get_mailbox("gmail-work")

        call_kwargs = mock_mailbox.call_args.kwargs
        assert call_kwargs["from_address"] == "alias@gmail.com"
        assert call_kwargs["from_name"] == "Atlas"

    @patch("read_no_evil_mcp.accounts.service.GmailConnector")
    @patch("read_no_evil_mcp.accounts.service.SecureMailbox")
    def test_get_mailbox_gmail_returns_secure_mailbox(
        self,
        mock_mailbox: MagicMock,
        mock_gmail_connector: MagicMock,
    ) -> None:
        """Test get_mailbox returns SecureMailbox for Gmail accounts."""
        accounts = [
            GmailAccountConfig(
                id="gmail-work",
                email="user@gmail.com",
                credentials_file="/path/to/creds.json",
            ),
        ]
        service = AccountService(accounts, MockCredentialBackend({}))

        result = service.get_mailbox("gmail-work")

        mock_mailbox.assert_called_once()
        assert result == mock_mailbox.return_value
