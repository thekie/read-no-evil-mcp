"""Tests for get_email tool."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from read_no_evil_mcp.models import Email, EmailAddress
from read_no_evil_mcp.tools.get_email import get_email_impl


class TestGetEmail:
    def test_returns_full_email_content(self) -> None:
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
        mock_service.__enter__ = MagicMock(return_value=mock_service)
        mock_service.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.get_email.create_service",
            return_value=mock_service,
        ):
            result = get_email_impl(folder="INBOX", uid=123)

        assert "Subject: Test Email" in result
        assert "From: Sender <sender@example.com>" in result
        assert "To: to@example.com" in result
        assert "Hello, World!" in result

    def test_email_not_found(self) -> None:
        """Test get_email with non-existent email."""
        mock_service = MagicMock()
        mock_service.get_email.return_value = None
        mock_service.__enter__ = MagicMock(return_value=mock_service)
        mock_service.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.get_email.create_service",
            return_value=mock_service,
        ):
            result = get_email_impl(folder="INBOX", uid=999)

        assert "Email not found" in result

    def test_html_only_email(self) -> None:
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
        mock_service.__enter__ = MagicMock(return_value=mock_service)
        mock_service.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.get_email.create_service",
            return_value=mock_service,
        ):
            result = get_email_impl(folder="INBOX", uid=123)

        assert "HTML content - plain text not available" in result
        assert "<p>HTML content</p>" in result
