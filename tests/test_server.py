"""Tests for MCP server."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from read_no_evil_mcp.models import Email, EmailAddress, EmailSummary, Folder
from read_no_evil_mcp.server import (
    _get_email_impl,
    _list_emails_impl,
    _list_folders_impl,
    mcp,
)


class TestMCPSetup:
    def test_mcp_server_name(self):
        """Test that the MCP server has the correct name."""
        assert mcp.name == "read-no-evil-mcp"

    def test_tools_registered(self):
        """Test that all expected tools are registered."""
        tool_names = set(mcp._tool_manager._tools.keys())
        assert tool_names == {"list_folders", "list_emails", "get_email"}


class TestListFolders:
    def test_returns_folder_names(self):
        """Test list_folders tool returns folder names."""
        mock_service = MagicMock()
        mock_service.list_folders.return_value = [
            Folder(name="INBOX"),
            Folder(name="Sent"),
        ]

        with patch("read_no_evil_mcp.server._create_service", return_value=mock_service):
            result = _list_folders_impl()

        assert "INBOX" in result
        assert "Sent" in result
        mock_service.connect.assert_called_once()
        mock_service.disconnect.assert_called_once()

    def test_empty_folders(self):
        """Test list_folders with no folders."""
        mock_service = MagicMock()
        mock_service.list_folders.return_value = []

        with patch("read_no_evil_mcp.server._create_service", return_value=mock_service):
            result = _list_folders_impl()

        assert "No folders found" in result


class TestListEmails:
    def test_returns_email_summaries(self):
        """Test list_emails tool returns email summaries."""
        mock_service = MagicMock()
        mock_service.fetch_emails.return_value = [
            EmailSummary(
                uid=1,
                folder="INBOX",
                subject="Test Subject",
                sender=EmailAddress(address="sender@example.com"),
                date=datetime(2026, 2, 3, 12, 0, 0),
                has_attachments=True,
            ),
        ]

        with patch("read_no_evil_mcp.server._create_service", return_value=mock_service):
            result = _list_emails_impl(folder="INBOX", days_back=7)

        assert "[1]" in result
        assert "Test Subject" in result
        assert "sender@example.com" in result
        assert "[+]" in result  # attachment marker

    def test_no_emails(self):
        """Test list_emails with no emails."""
        mock_service = MagicMock()
        mock_service.fetch_emails.return_value = []

        with patch("read_no_evil_mcp.server._create_service", return_value=mock_service):
            result = _list_emails_impl()

        assert "No emails found" in result

    def test_respects_limit_parameter(self):
        """Test list_emails respects limit parameter."""
        mock_service = MagicMock()
        mock_service.fetch_emails.return_value = []

        with patch("read_no_evil_mcp.server._create_service", return_value=mock_service):
            _list_emails_impl(folder="INBOX", limit=5)

        call_args = mock_service.fetch_emails.call_args
        assert call_args.kwargs["limit"] == 5

    def test_default_parameters(self):
        """Test list_emails uses default parameters."""
        mock_service = MagicMock()
        mock_service.fetch_emails.return_value = []

        with patch("read_no_evil_mcp.server._create_service", return_value=mock_service):
            _list_emails_impl()

        call_args = mock_service.fetch_emails.call_args
        assert call_args.args[0] == "INBOX"


class TestGetEmail:
    def test_returns_full_email_content(self):
        """Test get_email tool returns full email content."""
        mock_service = MagicMock()
        mock_service.get_email.return_value = Email(
            uid=123,
            folder="INBOX",
            subject="Test Email",
            sender=EmailAddress(name="Sender", address="sender@example.com"),
            date=datetime(2026, 2, 3, 12, 0, 0),
            to=[EmailAddress(address="to@example.com")],
            body_plain="Hello, World!",
            message_id="<abc@example.com>",
        )

        with patch("read_no_evil_mcp.server._create_service", return_value=mock_service):
            result = _get_email_impl(folder="INBOX", uid=123)

        assert "Subject: Test Email" in result
        assert "From: Sender <sender@example.com>" in result
        assert "To: to@example.com" in result
        assert "Hello, World!" in result

    def test_email_not_found(self):
        """Test get_email with non-existent email."""
        mock_service = MagicMock()
        mock_service.get_email.return_value = None

        with patch("read_no_evil_mcp.server._create_service", return_value=mock_service):
            result = _get_email_impl(folder="INBOX", uid=999)

        assert "Email not found" in result

    def test_html_only_email(self):
        """Test get_email with HTML-only content."""
        mock_service = MagicMock()
        mock_service.get_email.return_value = Email(
            uid=123,
            folder="INBOX",
            subject="HTML Email",
            sender=EmailAddress(address="sender@example.com"),
            date=datetime(2026, 2, 3, 12, 0, 0),
            body_html="<p>HTML content</p>",
        )

        with patch("read_no_evil_mcp.server._create_service", return_value=mock_service):
            result = _get_email_impl(folder="INBOX", uid=123)

        assert "HTML content - plain text not available" in result
        assert "<p>HTML content</p>" in result


class TestConnectionManagement:
    def test_disconnect_called_on_exception(self):
        """Test that disconnect is called even when exception occurs."""
        mock_service = MagicMock()
        mock_service.list_folders.side_effect = RuntimeError("Connection error")

        with patch("read_no_evil_mcp.server._create_service", return_value=mock_service):
            with pytest.raises(RuntimeError):
                _list_folders_impl()

        mock_service.disconnect.assert_called_once()
