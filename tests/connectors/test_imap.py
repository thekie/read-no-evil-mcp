"""Tests for IMAP connector."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from read_no_evil_mcp.connectors.imap import IMAPConnector, _parse_address, _parse_addresses
from read_no_evil_mcp.models import IMAPConfig


class TestParseAddress:
    def test_with_name(self):
        addr = _parse_address(("John Doe", "john@example.com"))
        assert addr.name == "John Doe"
        assert addr.address == "john@example.com"

    def test_without_name(self):
        addr = _parse_address(("", "john@example.com"))
        assert addr.name is None
        assert addr.address == "john@example.com"

    def test_none(self):
        assert _parse_address(None) is None


class TestParseAddresses:
    def test_multiple(self):
        addrs = _parse_addresses(
            (
                ("Alice", "alice@example.com"),
                ("Bob", "bob@example.com"),
            )
        )
        assert len(addrs) == 2
        assert addrs[0].name == "Alice"
        assert addrs[1].address == "bob@example.com"

    def test_empty(self):
        addrs = _parse_addresses(())
        assert addrs == []

    def test_filters_empty_addresses(self):
        addrs = _parse_addresses(
            (
                ("Alice", "alice@example.com"),
                ("", ""),
            )
        )
        assert len(addrs) == 1


class TestIMAPConnector:
    @pytest.fixture
    def config(self):
        return IMAPConfig(
            host="imap.example.com",
            username="user",
            password="secret",
        )

    def test_init(self, config):
        connector = IMAPConnector(config)
        assert connector.config == config
        assert connector._mailbox is None

    @patch("read_no_evil_mcp.connectors.imap.MailBox")
    def test_connect_ssl(self, mock_mailbox_class, config):
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox

        connector = IMAPConnector(config)
        connector.connect()

        mock_mailbox_class.assert_called_once_with("imap.example.com", 993)
        mock_mailbox.login.assert_called_once_with("user", "secret")

    @patch("read_no_evil_mcp.connectors.imap.MailBox")
    def test_disconnect(self, mock_mailbox_class, config):
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox

        connector = IMAPConnector(config)
        connector.connect()
        connector.disconnect()

        mock_mailbox.logout.assert_called_once()
        assert connector._mailbox is None

    @patch("read_no_evil_mcp.connectors.imap.MailBox")
    def test_context_manager(self, mock_mailbox_class, config):
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox

        with IMAPConnector(config) as connector:
            assert connector._mailbox is not None

        mock_mailbox.logout.assert_called_once()

    @patch("read_no_evil_mcp.connectors.imap.MailBox")
    def test_list_folders(self, mock_mailbox_class, config):
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

    def test_list_folders_not_connected(self, config):
        connector = IMAPConnector(config)
        with pytest.raises(RuntimeError, match="Not connected"):
            connector.list_folders()

    @patch("read_no_evil_mcp.connectors.imap.MailBox")
    def test_fetch_emails(self, mock_mailbox_class, config):
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox

        mock_msg = MagicMock()
        mock_msg.uid = "123"
        mock_msg.subject = "Test Subject"
        mock_msg.from_values.name = "Sender"
        mock_msg.from_values.email = "sender@example.com"
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

    @patch("read_no_evil_mcp.connectors.imap.MailBox")
    def test_fetch_emails_with_limit(self, mock_mailbox_class, config):
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox

        mock_msgs = []
        for i in range(10):
            mock_msg = MagicMock()
            mock_msg.uid = str(i)
            mock_msg.subject = f"Subject {i}"
            mock_msg.from_values.name = ""
            mock_msg.from_values.email = f"sender{i}@example.com"
            mock_msg.date = datetime(2026, 2, 3, 12, 0, 0)
            mock_msg.attachments = []
            mock_msgs.append(mock_msg)
        mock_mailbox.fetch.return_value = mock_msgs

        connector = IMAPConnector(config)
        connector.connect()
        emails = connector.fetch_emails("INBOX", lookback=timedelta(days=7), limit=3)

        assert len(emails) == 3

    def test_fetch_emails_not_connected(self, config):
        connector = IMAPConnector(config)
        with pytest.raises(RuntimeError, match="Not connected"):
            connector.fetch_emails("INBOX", lookback=timedelta(days=7))

    @patch("read_no_evil_mcp.connectors.imap.MailBox")
    def test_get_email(self, mock_mailbox_class, config):
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox

        mock_msg = MagicMock()
        mock_msg.uid = "123"
        mock_msg.subject = "Test Subject"
        mock_msg.from_values.name = "Sender"
        mock_msg.from_values.email = "sender@example.com"
        mock_msg.date = datetime(2026, 2, 3, 12, 0, 0)
        mock_msg.to_values = (("Recipient", "recipient@example.com"),)
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

    @patch("read_no_evil_mcp.connectors.imap.MailBox")
    def test_get_email_not_found(self, mock_mailbox_class, config):
        mock_mailbox = MagicMock()
        mock_mailbox_class.return_value = mock_mailbox
        mock_mailbox.fetch.return_value = []

        connector = IMAPConnector(config)
        connector.connect()
        email = connector.get_email("INBOX", 999)

        assert email is None

    def test_get_email_not_connected(self, config):
        connector = IMAPConnector(config)
        with pytest.raises(RuntimeError, match="Not connected"):
            connector.get_email("INBOX", 123)
