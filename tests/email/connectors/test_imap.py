"""Tests for IMAP connector."""

import logging
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from read_no_evil_mcp.email.connectors.imap import IMAPConnector
from read_no_evil_mcp.models import IMAPConfig, SMTPConfig


class TestIMAPConnector:
    @pytest.fixture
    def config(self) -> IMAPConfig:
        return IMAPConfig(
            host="imap.example.com",
            username="user",
            password="secret",
        )

    def test_init(self, config: IMAPConfig) -> None:
        connector = IMAPConnector(config)
        assert connector.config == config
        assert connector._mailbox is None

    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    def test_connect_ssl(self, mock_mailbox_class: MagicMock, config: IMAPConfig) -> None:
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox

        connector = IMAPConnector(config)
        connector.connect()

        mock_mailbox_class.assert_called_once_with("imap.example.com", 993)
        mock_mailbox.login.assert_called_once_with("user", "secret")

    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    def test_disconnect(self, mock_mailbox_class: MagicMock, config: IMAPConfig) -> None:
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox

        connector = IMAPConnector(config)
        connector.connect()
        connector.disconnect()

        mock_mailbox.logout.assert_called_once()
        assert connector._mailbox is None

    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    def test_context_manager(self, mock_mailbox_class: MagicMock, config: IMAPConfig) -> None:
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox

        with IMAPConnector(config) as connector:
            assert connector._mailbox is not None

        mock_mailbox.logout.assert_called_once()

    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    def test_list_folders(self, mock_mailbox_class: MagicMock, config: IMAPConfig) -> None:
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox

        mock_folder_info = MagicMock()
        mock_folder_info.name = "INBOX"
        mock_folder_info.delim = "/"
        mock_folder_info.flags = ("\\HasNoChildren",)
        mock_mailbox.folder.list.return_value = [mock_folder_info]

        connector = IMAPConnector(config)
        connector.connect()
        folders = connector.list_folders()

        assert len(folders) == 1
        assert folders[0].name == "INBOX"
        assert folders[0].delimiter == "/"

    def test_list_folders_not_connected(self, config: IMAPConfig) -> None:
        connector = IMAPConnector(config)
        with pytest.raises(RuntimeError, match="Not connected"):
            connector.list_folders()

    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    def test_fetch_emails(self, mock_mailbox_class: MagicMock, config: IMAPConfig) -> None:
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox

        mock_from = MagicMock()
        mock_from.name = "Sender"
        mock_from.email = "sender@example.com"

        mock_msg = MagicMock()
        mock_msg.uid = "123"
        mock_msg.subject = "Test Subject"
        mock_msg.from_values = mock_from
        mock_msg.date = datetime(2026, 2, 3, 12, 0, 0)
        mock_msg.attachments = []
        mock_msg.flags = ("\\Seen",)
        mock_mailbox.fetch.return_value = [mock_msg]

        connector = IMAPConnector(config)
        connector.connect()
        emails = connector.fetch_emails("INBOX", lookback=timedelta(days=7))

        assert len(emails) == 1
        assert emails[0].uid == 123
        assert emails[0].subject == "Test Subject"
        assert emails[0].sender.address == "sender@example.com"
        assert emails[0].is_seen is True

    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    def test_fetch_emails_unseen(self, mock_mailbox_class: MagicMock, config: IMAPConfig) -> None:
        """Test fetch_emails correctly identifies unseen messages."""
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox

        mock_from = MagicMock()
        mock_from.name = "Sender"
        mock_from.email = "sender@example.com"

        mock_msg = MagicMock()
        mock_msg.uid = "123"
        mock_msg.subject = "Test Subject"
        mock_msg.from_values = mock_from
        mock_msg.date = datetime(2026, 2, 3, 12, 0, 0)
        mock_msg.attachments = []
        mock_msg.flags = ()  # No flags = unseen
        mock_mailbox.fetch.return_value = [mock_msg]

        connector = IMAPConnector(config)
        connector.connect()
        emails = connector.fetch_emails("INBOX", lookback=timedelta(days=7))

        assert len(emails) == 1
        assert emails[0].is_seen is False

    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    def test_fetch_emails_with_limit(
        self, mock_mailbox_class: MagicMock, config: IMAPConfig
    ) -> None:
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox

        mock_msgs = []
        for i in range(10):
            mock_from = MagicMock()
            mock_from.name = ""
            mock_from.email = f"sender{i}@example.com"

            mock_msg = MagicMock()
            mock_msg.uid = str(i)
            mock_msg.subject = f"Subject {i}"
            mock_msg.from_values = mock_from
            mock_msg.date = datetime(2026, 2, 3, 12, 0, 0)
            mock_msg.attachments = []
            mock_msg.flags = ()
            mock_msgs.append(mock_msg)
        mock_mailbox.fetch.return_value = mock_msgs

        connector = IMAPConnector(config)
        connector.connect()
        emails = connector.fetch_emails("INBOX", lookback=timedelta(days=7), limit=3)

        assert len(emails) == 3

    def test_fetch_emails_not_connected(self, config: IMAPConfig) -> None:
        connector = IMAPConnector(config)
        with pytest.raises(RuntimeError, match="Not connected"):
            connector.fetch_emails("INBOX", lookback=timedelta(days=7))

    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    def test_get_email(self, mock_mailbox_class: MagicMock, config: IMAPConfig) -> None:
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox

        mock_from = MagicMock()
        mock_from.name = "Sender"
        mock_from.email = "sender@example.com"

        mock_to = MagicMock()
        mock_to.name = "Recipient"
        mock_to.email = "recipient@example.com"

        mock_msg = MagicMock()
        mock_msg.uid = "123"
        mock_msg.subject = "Test Subject"
        mock_msg.from_values = mock_from
        mock_msg.date = datetime(2026, 2, 3, 12, 0, 0)
        mock_msg.to_values = (mock_to,)
        mock_msg.cc_values = ()
        mock_msg.text = "Plain text body"
        mock_msg.html = "<p>HTML body</p>"
        mock_msg.attachments = []
        mock_msg.headers = {"message-id": ["<abc@example.com>"]}
        mock_msg.flags = ("\\Seen",)
        mock_mailbox.fetch.return_value = [mock_msg]

        connector = IMAPConnector(config)
        connector.connect()
        email = connector.get_email("INBOX", 123)

        assert email is not None
        assert email.uid == 123
        assert email.body_plain == "Plain text body"
        assert email.body_html == "<p>HTML body</p>"
        assert len(email.to) == 1
        assert email.is_seen is True

    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    def test_get_email_unseen(self, mock_mailbox_class: MagicMock, config: IMAPConfig) -> None:
        """Test get_email correctly identifies unseen messages."""
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox

        mock_from = MagicMock()
        mock_from.name = "Sender"
        mock_from.email = "sender@example.com"

        mock_msg = MagicMock()
        mock_msg.uid = "123"
        mock_msg.subject = "Test Subject"
        mock_msg.from_values = mock_from
        mock_msg.date = datetime(2026, 2, 3, 12, 0, 0)
        mock_msg.to_values = ()
        mock_msg.cc_values = ()
        mock_msg.text = "Plain text body"
        mock_msg.html = None
        mock_msg.attachments = []
        mock_msg.headers = {}
        mock_msg.flags = ()  # No flags = unseen
        mock_mailbox.fetch.return_value = [mock_msg]

        connector = IMAPConnector(config)
        connector.connect()
        email = connector.get_email("INBOX", 123)

        assert email is not None
        assert email.is_seen is False

    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    def test_get_email_not_found(self, mock_mailbox_class: MagicMock, config: IMAPConfig) -> None:
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox
        mock_mailbox.fetch.return_value = []

        connector = IMAPConnector(config)
        connector.connect()
        email = connector.get_email("INBOX", 999)

        assert email is None

    def test_get_email_not_connected(self, config: IMAPConfig) -> None:
        connector = IMAPConnector(config)
        with pytest.raises(RuntimeError, match="Not connected"):
            connector.get_email("INBOX", 123)

    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    def test_fetch_emails_skips_none_uid(
        self, mock_mailbox_class: MagicMock, config: IMAPConfig, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test fetch_emails skips messages with None uid and returns only valid ones."""
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox

        mock_from = MagicMock()
        mock_from.name = "Sender"
        mock_from.email = "sender@example.com"

        valid_msg = MagicMock()
        valid_msg.uid = "456"
        valid_msg.subject = "Valid Email"
        valid_msg.from_values = mock_from
        valid_msg.date = datetime(2026, 2, 3, 12, 0, 0)
        valid_msg.attachments = []
        valid_msg.flags = ()

        none_uid_msg = MagicMock()
        none_uid_msg.uid = None
        none_uid_msg.subject = "Ghost Email"
        none_uid_msg.from_values = mock_from
        none_uid_msg.date = datetime(2026, 2, 3, 12, 0, 0)
        none_uid_msg.attachments = []
        none_uid_msg.flags = ()

        mock_mailbox.fetch.return_value = [none_uid_msg, valid_msg]

        connector = IMAPConnector(config)
        connector.connect()
        with caplog.at_level(logging.WARNING, logger="read_no_evil_mcp.email.connectors.imap"):
            emails = connector.fetch_emails("INBOX", lookback=timedelta(days=7))

        assert len(emails) == 1
        assert emails[0].uid == 456
        assert emails[0].subject == "Valid Email"
        assert "Skipping email with missing UID" in caplog.text

    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    def test_fetch_emails_all_none_uid_returns_empty(
        self, mock_mailbox_class: MagicMock, config: IMAPConfig
    ) -> None:
        """Test fetch_emails returns empty list when all messages have None uid."""
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox

        mock_from = MagicMock()
        mock_from.name = "Sender"
        mock_from.email = "sender@example.com"

        none_msg1 = MagicMock()
        none_msg1.uid = None
        none_msg1.subject = "Ghost 1"
        none_msg1.from_values = mock_from
        none_msg1.date = datetime(2026, 2, 3, 12, 0, 0)
        none_msg1.attachments = []
        none_msg1.flags = ()

        none_msg2 = MagicMock()
        none_msg2.uid = None
        none_msg2.subject = "Ghost 2"
        none_msg2.from_values = mock_from
        none_msg2.date = datetime(2026, 2, 3, 12, 0, 0)
        none_msg2.attachments = []
        none_msg2.flags = ()

        mock_mailbox.fetch.return_value = [none_msg1, none_msg2]

        connector = IMAPConnector(config)
        connector.connect()
        emails = connector.fetch_emails("INBOX", lookback=timedelta(days=7))

        assert emails == []

    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    def test_get_email_returns_none_for_none_uid(
        self, mock_mailbox_class: MagicMock, config: IMAPConfig, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test get_email returns None when the fetched message has None uid."""
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox

        mock_from = MagicMock()
        mock_from.name = "Sender"
        mock_from.email = "sender@example.com"

        mock_msg = MagicMock()
        mock_msg.uid = None
        mock_msg.subject = "Ghost Email"
        mock_msg.from_values = mock_from
        mock_msg.date = datetime(2026, 2, 3, 12, 0, 0)
        mock_msg.to_values = ()
        mock_msg.cc_values = ()
        mock_msg.text = "Body"
        mock_msg.html = None
        mock_msg.attachments = []
        mock_msg.headers = {}
        mock_msg.flags = ()
        mock_mailbox.fetch.return_value = [mock_msg]

        connector = IMAPConnector(config)
        connector.connect()
        with caplog.at_level(logging.WARNING, logger="read_no_evil_mcp.email.connectors.imap"):
            email = connector.get_email("INBOX", 123)

        assert email is None
        assert "Skipping email with missing UID" in caplog.text

    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    def test_move_email_success(self, mock_mailbox_class: MagicMock, config: IMAPConfig) -> None:
        """Test move_email moves email to target folder."""
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox

        # Mock email exists
        mock_msg = MagicMock()
        mock_msg.uid = "123"
        mock_mailbox.fetch.return_value = [mock_msg]

        connector = IMAPConnector(config)
        connector.connect()
        result = connector.move_email("INBOX", 123, "Archive")

        assert result is True
        mock_mailbox.folder.set.assert_called_with("INBOX")
        mock_mailbox.move.assert_called_once_with("123", "Archive")

    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    def test_move_email_to_spam(self, mock_mailbox_class: MagicMock, config: IMAPConfig) -> None:
        """Test move_email can move to Spam folder."""
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox

        # Mock email exists
        mock_msg = MagicMock()
        mock_msg.uid = "456"
        mock_mailbox.fetch.return_value = [mock_msg]

        connector = IMAPConnector(config)
        connector.connect()
        result = connector.move_email("INBOX", 456, "Spam")

        assert result is True
        mock_mailbox.move.assert_called_once_with("456", "Spam")

    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    def test_move_email_to_different_folder(
        self, mock_mailbox_class: MagicMock, config: IMAPConfig
    ) -> None:
        """Test move_email moves to various target folders."""
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox

        # Mock email exists
        mock_msg = MagicMock()
        mock_msg.uid = "789"
        mock_mailbox.fetch.return_value = [mock_msg]

        connector = IMAPConnector(config)
        connector.connect()
        result = connector.move_email("INBOX", 789, "Important")

        assert result is True
        mock_mailbox.move.assert_called_once_with("789", "Important")

    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    def test_move_email_not_found(self, mock_mailbox_class: MagicMock, config: IMAPConfig) -> None:
        """Test move_email returns False when email not found."""
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox

        # Mock email not found
        mock_mailbox.fetch.return_value = []

        connector = IMAPConnector(config)
        connector.connect()
        result = connector.move_email("INBOX", 999, "Archive")

        assert result is False
        mock_mailbox.move.assert_not_called()

    def test_move_email_not_connected(self, config: IMAPConfig) -> None:
        """Test move_email raises RuntimeError when not connected."""
        connector = IMAPConnector(config)
        with pytest.raises(RuntimeError, match="Not connected"):
            connector.move_email("INBOX", 123, "Archive")

    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    def test_delete_email(self, mock_mailbox_class: MagicMock, config: IMAPConfig) -> None:
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox

        connector = IMAPConnector(config)
        connector.connect()
        result = connector.delete_email("INBOX", 123)

        assert result is True
        mock_mailbox.folder.set.assert_called_with("INBOX")
        mock_mailbox.delete.assert_called_once_with("123")
        mock_mailbox.expunge.assert_called_once()

    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    def test_delete_email_different_folder(
        self, mock_mailbox_class: MagicMock, config: IMAPConfig
    ) -> None:
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox

        connector = IMAPConnector(config)
        connector.connect()
        result = connector.delete_email("Sent", 456)

        assert result is True
        mock_mailbox.folder.set.assert_called_with("Sent")
        mock_mailbox.delete.assert_called_once_with("456")
        mock_mailbox.expunge.assert_called_once()

    def test_delete_email_not_connected(self, config: IMAPConfig) -> None:
        connector = IMAPConnector(config)
        with pytest.raises(RuntimeError, match="Not connected"):
            connector.delete_email("INBOX", 123)


class TestIMAPConnectorWithSMTP:
    """Tests for IMAPConnector SMTP capabilities."""

    @pytest.fixture
    def imap_config(self) -> IMAPConfig:
        return IMAPConfig(
            host="imap.example.com",
            username="user",
            password=SecretStr("secret"),
        )

    @pytest.fixture
    def smtp_config(self) -> SMTPConfig:
        return SMTPConfig(
            host="smtp.example.com",
            port=587,
            username="user",
            password=SecretStr("secret"),
            ssl=False,
        )

    def test_can_send_without_smtp(self, imap_config: IMAPConfig) -> None:
        """Test can_send returns False when SMTP is not configured."""
        connector = IMAPConnector(imap_config)
        assert connector.can_send() is False

    def test_can_send_with_smtp(self, imap_config: IMAPConfig, smtp_config: SMTPConfig) -> None:
        """Test can_send returns True when SMTP is configured."""
        connector = IMAPConnector(imap_config, smtp_config=smtp_config)
        assert connector.can_send() is True

    def test_send_without_smtp_raises(self, imap_config: IMAPConfig) -> None:
        """Test send raises NotImplementedError when SMTP is not configured."""
        connector = IMAPConnector(imap_config)
        with pytest.raises(NotImplementedError) as exc_info:
            connector.send(
                from_address="sender@example.com",
                to=["recipient@example.com"],
                subject="Test",
                body="Test body",
            )
        assert "does not support sending" in str(exc_info.value)

    @patch("read_no_evil_mcp.email.connectors.imap.SMTPConnector")
    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    def test_connect_with_smtp(
        self,
        mock_mailbox_class: MagicMock,
        mock_smtp_connector_class: MagicMock,
        imap_config: IMAPConfig,
        smtp_config: SMTPConfig,
    ) -> None:
        """Test connect only establishes IMAP connection, not SMTP."""
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox

        connector = IMAPConnector(imap_config, smtp_config=smtp_config)
        connector.connect()

        mock_mailbox_class.assert_called_once()
        mock_mailbox.login.assert_called_once()
        mock_smtp_connector_class.assert_not_called()

    @patch("read_no_evil_mcp.email.connectors.imap.SMTPConnector")
    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    def test_disconnect_with_smtp(
        self,
        mock_mailbox_class: MagicMock,
        mock_smtp_connector_class: MagicMock,
        imap_config: IMAPConfig,
        smtp_config: SMTPConfig,
    ) -> None:
        """Test disconnect closes both IMAP and SMTP connections after send."""
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox
        mock_smtp_connector = MagicMock()
        mock_smtp_connector_class.return_value = mock_smtp_connector
        mock_smtp_connector.build_message.return_value = MagicMock(
            as_bytes=MagicMock(return_value=b"msg")
        )

        connector = IMAPConnector(imap_config, smtp_config=smtp_config)
        connector.connect()
        # Trigger lazy SMTP init by sending
        connector.send(
            from_address="sender@example.com",
            to=["recipient@example.com"],
            subject="Test",
            body="Test body",
        )
        connector.disconnect()

        mock_mailbox.logout.assert_called_once()
        mock_smtp_connector.disconnect.assert_called_once()

    @patch("read_no_evil_mcp.email.connectors.imap.SMTPConnector")
    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    def test_send_email(
        self,
        mock_mailbox_class: MagicMock,
        mock_smtp_connector_class: MagicMock,
        imap_config: IMAPConfig,
        smtp_config: SMTPConfig,
    ) -> None:
        """Test sending email via IMAP connector with SMTP."""
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox
        mock_smtp_connector = MagicMock()
        mock_smtp_connector_class.return_value = mock_smtp_connector
        mock_smtp_connector.build_message.return_value = MagicMock(
            as_bytes=MagicMock(return_value=b"msg")
        )

        connector = IMAPConnector(imap_config, smtp_config=smtp_config)
        connector.connect()

        result = connector.send(
            from_address="sender@example.com",
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Test body",
        )

        assert result is True
        mock_smtp_connector.send_message.assert_called_once()

    @patch("read_no_evil_mcp.email.connectors.imap.SMTPConnector")
    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    def test_send_email_with_reply_to(
        self,
        mock_mailbox_class: MagicMock,
        mock_smtp_connector_class: MagicMock,
        imap_config: IMAPConfig,
        smtp_config: SMTPConfig,
    ) -> None:
        """Test sending email with reply_to parameter."""
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox
        mock_smtp_connector = MagicMock()
        mock_smtp_connector_class.return_value = mock_smtp_connector
        mock_smtp_connector.build_message.return_value = MagicMock(
            as_bytes=MagicMock(return_value=b"msg")
        )

        connector = IMAPConnector(imap_config, smtp_config=smtp_config)
        connector.connect()

        result = connector.send(
            from_address="sender@example.com",
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Test body",
            reply_to="replies@example.com",
        )

        assert result is True
        # Verify reply_to was passed to build_message
        mock_smtp_connector.build_message.assert_called_once_with(
            from_address="sender@example.com",
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Test body",
            from_name=None,
            cc=None,
            reply_to="replies@example.com",
            attachments=None,
        )

    @patch("read_no_evil_mcp.email.connectors.imap.SMTPConnector")
    def test_send_without_imap_connect_lazy_inits_smtp(
        self,
        mock_smtp_connector_class: MagicMock,
        imap_config: IMAPConfig,
        smtp_config: SMTPConfig,
    ) -> None:
        """Test send lazy-initializes SMTP even without prior IMAP connect."""
        mock_smtp_connector = MagicMock()
        mock_smtp_connector_class.return_value = mock_smtp_connector
        mock_smtp_connector.build_message.return_value = MagicMock(
            as_bytes=MagicMock(return_value=b"msg")
        )

        connector = IMAPConnector(imap_config, smtp_config=smtp_config)
        result = connector.send(
            from_address="sender@example.com",
            to=["recipient@example.com"],
            subject="Test",
            body="Test body",
        )

        assert result is True
        mock_smtp_connector_class.assert_called_once_with(smtp_config)
        mock_smtp_connector.connect.assert_called_once()
        mock_smtp_connector.send_message.assert_called_once()

    @patch("read_no_evil_mcp.email.connectors.imap.SMTPConnector")
    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    def test_send_saves_to_sent_folder(
        self,
        mock_mailbox_class: MagicMock,
        mock_smtp_connector_class: MagicMock,
        imap_config: IMAPConfig,
        smtp_config: SMTPConfig,
    ) -> None:
        """Test send appends email to the Sent folder via IMAP."""
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox
        mock_smtp_connector = MagicMock()
        mock_smtp_connector_class.return_value = mock_smtp_connector
        mock_msg = MagicMock()
        mock_msg.as_bytes.return_value = b"Subject: Test Subject\r\n\r\nTest body"
        mock_smtp_connector.build_message.return_value = mock_msg

        imap_config_with_sent = IMAPConfig(
            host="imap.example.com",
            username="user",
            password=SecretStr("secret"),
            sent_folder="Sent",
        )
        connector = IMAPConnector(imap_config_with_sent, smtp_config=smtp_config)
        connector.connect()

        connector.send(
            from_address="sender@example.com",
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Test body",
        )

        mock_mailbox.append.assert_called_once()
        call_args = mock_mailbox.append.call_args
        assert call_args.args[1] == "Sent"
        # Verify the appended message contains the subject
        appended_bytes = call_args.args[0]
        assert b"Test Subject" in appended_bytes
        # Verify \Seen flag is set
        assert call_args.kwargs["flag_set"] == [r"\Seen"]

    @patch("read_no_evil_mcp.email.connectors.imap.SMTPConnector")
    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    def test_send_custom_sent_folder(
        self,
        mock_mailbox_class: MagicMock,
        mock_smtp_connector_class: MagicMock,
        imap_config: IMAPConfig,
        smtp_config: SMTPConfig,
    ) -> None:
        """Test send uses custom sent folder name (e.g., Gmail)."""
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox
        mock_smtp_connector = MagicMock()
        mock_smtp_connector_class.return_value = mock_smtp_connector
        mock_smtp_connector.build_message.return_value = MagicMock(
            as_bytes=MagicMock(return_value=b"msg")
        )

        imap_config_gmail = IMAPConfig(
            host="imap.example.com",
            username="user",
            password=SecretStr("secret"),
            sent_folder="[Gmail]/Sent Mail",
        )
        connector = IMAPConnector(imap_config_gmail, smtp_config=smtp_config)
        connector.connect()

        connector.send(
            from_address="sender@example.com",
            to=["recipient@example.com"],
            subject="Test",
            body="Body",
        )

        call_args = mock_mailbox.append.call_args
        assert call_args.args[1] == "[Gmail]/Sent Mail"

    @patch("read_no_evil_mcp.email.connectors.imap.SMTPConnector")
    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    def test_send_skips_save_when_sent_folder_none(
        self,
        mock_mailbox_class: MagicMock,
        mock_smtp_connector_class: MagicMock,
        imap_config: IMAPConfig,
        smtp_config: SMTPConfig,
    ) -> None:
        """Test send does not append when sent_folder is None."""
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox
        mock_smtp_connector = MagicMock()
        mock_smtp_connector_class.return_value = mock_smtp_connector
        mock_smtp_connector.build_message.return_value = MagicMock(
            as_bytes=MagicMock(return_value=b"msg")
        )

        imap_config_no_sent = IMAPConfig(
            host="imap.example.com",
            username="user",
            password=SecretStr("secret"),
            sent_folder=None,
        )
        connector = IMAPConnector(imap_config_no_sent, smtp_config=smtp_config)
        connector.connect()

        result = connector.send(
            from_address="sender@example.com",
            to=["recipient@example.com"],
            subject="Test",
            body="Body",
        )

        assert result is True
        mock_smtp_connector.send_message.assert_called_once()
        mock_mailbox.append.assert_not_called()

    @patch("read_no_evil_mcp.email.connectors.imap.SMTPConnector")
    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    def test_send_default_sent_folder(
        self,
        mock_mailbox_class: MagicMock,
        mock_smtp_connector_class: MagicMock,
        imap_config: IMAPConfig,
        smtp_config: SMTPConfig,
    ) -> None:
        """Test send defaults to 'Sent' folder when not specified."""
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox
        mock_smtp_connector = MagicMock()
        mock_smtp_connector_class.return_value = mock_smtp_connector
        mock_smtp_connector.build_message.return_value = MagicMock(
            as_bytes=MagicMock(return_value=b"msg")
        )

        connector = IMAPConnector(imap_config, smtp_config=smtp_config)
        connector.connect()

        connector.send(
            from_address="sender@example.com",
            to=["recipient@example.com"],
            subject="Test",
            body="Body",
        )

        call_args = mock_mailbox.append.call_args
        assert call_args.args[1] == "Sent"

    @patch("read_no_evil_mcp.email.connectors.imap.SMTPConnector")
    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    def test_connect_does_not_open_smtp(
        self,
        mock_mailbox_class: MagicMock,
        mock_smtp_connector_class: MagicMock,
        imap_config: IMAPConfig,
        smtp_config: SMTPConfig,
    ) -> None:
        """Test connect with smtp_config does not instantiate or connect SMTPConnector."""
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox

        connector = IMAPConnector(imap_config, smtp_config=smtp_config)
        connector.connect()

        mock_smtp_connector_class.assert_not_called()
        assert connector._smtp_connector is None

    @patch("read_no_evil_mcp.email.connectors.imap.SMTPConnector")
    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    def test_send_lazy_initializes_smtp(
        self,
        mock_mailbox_class: MagicMock,
        mock_smtp_connector_class: MagicMock,
        imap_config: IMAPConfig,
        smtp_config: SMTPConfig,
    ) -> None:
        """Test send creates and connects SMTPConnector on first call."""
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox
        mock_smtp_connector = MagicMock()
        mock_smtp_connector_class.return_value = mock_smtp_connector
        mock_smtp_connector.build_message.return_value = MagicMock(
            as_bytes=MagicMock(return_value=b"msg")
        )

        connector = IMAPConnector(imap_config, smtp_config=smtp_config)
        connector.connect()

        # Before send, no SMTP connector exists
        assert connector._smtp_connector is None

        connector.send(
            from_address="sender@example.com",
            to=["recipient@example.com"],
            subject="Test",
            body="Test body",
        )

        # After send, SMTP connector was created and connected
        mock_smtp_connector_class.assert_called_once_with(smtp_config)
        mock_smtp_connector.connect.assert_called_once()
        mock_smtp_connector.send_message.assert_called_once()

    @patch("read_no_evil_mcp.email.connectors.imap.SMTPConnector")
    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    def test_disconnect_without_send_skips_smtp(
        self,
        mock_mailbox_class: MagicMock,
        mock_smtp_connector_class: MagicMock,
        imap_config: IMAPConfig,
        smtp_config: SMTPConfig,
    ) -> None:
        """Test disconnect after connect without send does not disconnect SMTP."""
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox

        connector = IMAPConnector(imap_config, smtp_config=smtp_config)
        connector.connect()
        connector.disconnect()

        mock_smtp_connector_class.assert_not_called()
        mock_mailbox.logout.assert_called_once()
