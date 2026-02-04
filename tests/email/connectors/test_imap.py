"""Tests for IMAP connector."""

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
        mock_mailbox.fetch.return_value = [mock_msg]

        connector = IMAPConnector(config)
        connector.connect()
        emails = connector.fetch_emails("INBOX", lookback=timedelta(days=7))

        assert len(emails) == 1
        assert emails[0].uid == 123
        assert emails[0].subject == "Test Subject"
        assert emails[0].sender.address == "sender@example.com"

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
        mock_mailbox.fetch.return_value = [mock_msg]

        connector = IMAPConnector(config)
        connector.connect()
        email = connector.get_email("INBOX", 123)

        assert email is not None
        assert email.uid == 123
        assert email.body_plain == "Plain text body"
        assert email.body_html == "<p>HTML body</p>"
        assert len(email.to) == 1

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
    def test_delete_email(self, mock_mailbox_class: MagicMock, config: IMAPConfig) -> None:
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox

        connector = IMAPConnector(config)
        connector.connect()
        result = connector.delete_email("INBOX", 123)

        assert result is True
        mock_mailbox.folder.set.assert_called_with("INBOX")
        mock_mailbox.delete.assert_called_once_with("123")

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

    def test_can_send_with_smtp(
        self, imap_config: IMAPConfig, smtp_config: SMTPConfig
    ) -> None:
        """Test can_send returns True when SMTP is configured."""
        connector = IMAPConnector(imap_config, smtp_config=smtp_config)
        assert connector.can_send() is True

    def test_send_without_smtp_raises(self, imap_config: IMAPConfig) -> None:
        """Test send raises NotImplementedError when SMTP is not configured."""
        connector = IMAPConnector(imap_config)
        with pytest.raises(NotImplementedError) as exc_info:
            connector.send(
                from_addr="sender@example.com",
                to=["recipient@example.com"],
                subject="Test",
                body="Test body",
            )
        assert "does not support sending" in str(exc_info.value)

    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    @patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP")
    def test_connect_with_smtp(
        self,
        mock_smtp_class: MagicMock,
        mock_mailbox_class: MagicMock,
        imap_config: IMAPConfig,
        smtp_config: SMTPConfig,
    ) -> None:
        """Test connect establishes both IMAP and SMTP connections."""
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox
        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp

        connector = IMAPConnector(imap_config, smtp_config=smtp_config)
        connector.connect()

        mock_mailbox_class.assert_called_once()
        mock_smtp_class.assert_called_once_with("smtp.example.com", 587)
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once()

    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    @patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP")
    def test_disconnect_with_smtp(
        self,
        mock_smtp_class: MagicMock,
        mock_mailbox_class: MagicMock,
        imap_config: IMAPConfig,
        smtp_config: SMTPConfig,
    ) -> None:
        """Test disconnect closes both IMAP and SMTP connections."""
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox
        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp

        connector = IMAPConnector(imap_config, smtp_config=smtp_config)
        connector.connect()
        connector.disconnect()

        mock_mailbox.logout.assert_called_once()
        mock_smtp.quit.assert_called_once()

    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    @patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP")
    def test_send_email(
        self,
        mock_smtp_class: MagicMock,
        mock_mailbox_class: MagicMock,
        imap_config: IMAPConfig,
        smtp_config: SMTPConfig,
    ) -> None:
        """Test sending email via IMAP connector with SMTP."""
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox
        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp

        connector = IMAPConnector(imap_config, smtp_config=smtp_config)
        connector.connect()

        result = connector.send(
            from_addr="sender@example.com",
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Test body",
        )

        assert result is True
        mock_smtp.sendmail.assert_called_once()

    @patch("read_no_evil_mcp.email.connectors.imap.MailBox")
    @patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP")
    def test_send_email_with_reply_to(
        self,
        mock_smtp_class: MagicMock,
        mock_mailbox_class: MagicMock,
        imap_config: IMAPConfig,
        smtp_config: SMTPConfig,
    ) -> None:
        """Test sending email with reply_to parameter."""
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox
        mock_smtp = MagicMock()
        mock_smtp_class.return_value = mock_smtp

        connector = IMAPConnector(imap_config, smtp_config=smtp_config)
        connector.connect()

        result = connector.send(
            from_addr="sender@example.com",
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Test body",
            reply_to="replies@example.com",
        )

        assert result is True
        call_args = mock_smtp.sendmail.call_args
        msg_str = call_args[0][2]
        assert "Reply-To: replies@example.com" in msg_str

    def test_send_not_connected_raises(
        self, imap_config: IMAPConfig, smtp_config: SMTPConfig
    ) -> None:
        """Test send raises RuntimeError when not connected."""
        connector = IMAPConnector(imap_config, smtp_config=smtp_config)
        with pytest.raises(RuntimeError, match="Not connected"):
            connector.send(
                from_addr="sender@example.com",
                to=["recipient@example.com"],
                subject="Test",
                body="Test body",
            )
