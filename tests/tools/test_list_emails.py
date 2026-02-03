"""Tests for list_emails tool."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from read_no_evil_mcp.models import EmailAddress, EmailSummary
from read_no_evil_mcp.tools.list_emails import list_emails


class TestListEmails:
    def test_returns_email_summaries(self) -> None:
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
        mock_service.__enter__ = MagicMock(return_value=mock_service)
        mock_service.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.list_emails.create_service",
            return_value=mock_service,
        ):
            result = list_emails.fn(folder="INBOX", days_back=7)

        assert "[1]" in result
        assert "Test Subject" in result
        assert "sender@example.com" in result
        assert "[+]" in result  # attachment marker

    def test_no_emails(self) -> None:
        """Test list_emails with no emails."""
        mock_service = MagicMock()
        mock_service.fetch_emails.return_value = []
        mock_service.__enter__ = MagicMock(return_value=mock_service)
        mock_service.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.list_emails.create_service",
            return_value=mock_service,
        ):
            result = list_emails.fn()

        assert "No emails found" in result

    def test_respects_limit_parameter(self) -> None:
        """Test list_emails respects limit parameter."""
        mock_service = MagicMock()
        mock_service.fetch_emails.return_value = []
        mock_service.__enter__ = MagicMock(return_value=mock_service)
        mock_service.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.list_emails.create_service",
            return_value=mock_service,
        ):
            list_emails.fn(folder="INBOX", limit=5)

        call_args = mock_service.fetch_emails.call_args
        assert call_args.kwargs["limit"] == 5

    def test_default_parameters(self) -> None:
        """Test list_emails uses default parameters."""
        mock_service = MagicMock()
        mock_service.fetch_emails.return_value = []
        mock_service.__enter__ = MagicMock(return_value=mock_service)
        mock_service.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.list_emails.create_service",
            return_value=mock_service,
        ):
            list_emails.fn()

        call_args = mock_service.fetch_emails.call_args
        assert call_args.args[0] == "INBOX"
