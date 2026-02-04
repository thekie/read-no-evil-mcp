"""Tests for get_email tool."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from read_no_evil_mcp.accounts.permissions import PermissionChecker
from read_no_evil_mcp.exceptions import PermissionDeniedError
from read_no_evil_mcp.mailbox import PromptInjectionError
from read_no_evil_mcp.models import Email, EmailAddress, ScanResult
from read_no_evil_mcp.tools.get_email import get_email


def _mock_permission_checker() -> MagicMock:
    """Create a mock permission checker that allows all operations."""
    checker = MagicMock(spec=PermissionChecker)
    return checker


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

        with (
            patch(
                "read_no_evil_mcp.tools.get_email.create_securemailbox",
                return_value=mock_service,
            ),
            patch(
                "read_no_evil_mcp.tools.get_email.get_permission_checker",
                return_value=_mock_permission_checker(),
            ),
        ):
            result = get_email.fn(account="work", folder="INBOX", uid=123)

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

        with (
            patch(
                "read_no_evil_mcp.tools.get_email.create_securemailbox",
                return_value=mock_service,
            ),
            patch(
                "read_no_evil_mcp.tools.get_email.get_permission_checker",
                return_value=_mock_permission_checker(),
            ),
        ):
            result = get_email.fn(account="work", folder="INBOX", uid=999)

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

        with (
            patch(
                "read_no_evil_mcp.tools.get_email.create_securemailbox",
                return_value=mock_service,
            ),
            patch(
                "read_no_evil_mcp.tools.get_email.get_permission_checker",
                return_value=_mock_permission_checker(),
            ),
        ):
            result = get_email.fn(account="work", folder="INBOX", uid=123)

        assert "HTML content - plain text not available" in result
        assert "<p>HTML content</p>" in result

    def test_blocked_email(self) -> None:
        """Test get_email with prompt injection detected."""
        mock_service = MagicMock()
        scan_result = ScanResult(
            is_safe=False,
            score=0.8,
            detected_patterns=["ignore_instructions", "you_are_now"],
        )
        mock_service.get_email.side_effect = PromptInjectionError(
            scan_result, email_uid=123, folder="INBOX"
        )
        mock_service.__enter__ = MagicMock(return_value=mock_service)
        mock_service.__exit__ = MagicMock(return_value=None)

        with (
            patch(
                "read_no_evil_mcp.tools.get_email.create_securemailbox",
                return_value=mock_service,
            ),
            patch(
                "read_no_evil_mcp.tools.get_email.get_permission_checker",
                return_value=_mock_permission_checker(),
            ),
        ):
            result = get_email.fn(account="work", folder="INBOX", uid=123)

        assert "BLOCKED" in result
        assert "INBOX/123" in result
        assert "ignore_instructions" in result
        assert "you_are_now" in result
        assert "0.80" in result  # Score
        assert "prompt injection" in result.lower()

    def test_blocked_email_single_pattern(self) -> None:
        """Test blocked email message with single pattern."""
        mock_service = MagicMock()
        scan_result = ScanResult(
            is_safe=False,
            score=0.5,
            detected_patterns=["system_tag"],
        )
        mock_service.get_email.side_effect = PromptInjectionError(
            scan_result, email_uid=456, folder="Sent"
        )
        mock_service.__enter__ = MagicMock(return_value=mock_service)
        mock_service.__exit__ = MagicMock(return_value=None)

        with (
            patch(
                "read_no_evil_mcp.tools.get_email.create_securemailbox",
                return_value=mock_service,
            ),
            patch(
                "read_no_evil_mcp.tools.get_email.get_permission_checker",
                return_value=_mock_permission_checker(),
            ),
        ):
            result = get_email.fn(account="work", folder="Sent", uid=456)

        assert "BLOCKED" in result
        assert "Sent/456" in result
        assert "system_tag" in result

    def test_passes_account_to_create_securemailbox(self) -> None:
        """Test get_email passes account to create_securemailbox."""
        mock_service = MagicMock()
        mock_service.get_email.return_value = None
        mock_service.__enter__ = MagicMock(return_value=mock_service)
        mock_service.__exit__ = MagicMock(return_value=None)

        with (
            patch(
                "read_no_evil_mcp.tools.get_email.create_securemailbox",
                return_value=mock_service,
            ) as mock_create,
            patch(
                "read_no_evil_mcp.tools.get_email.get_permission_checker",
                return_value=_mock_permission_checker(),
            ),
        ):
            get_email.fn(account="personal", folder="INBOX", uid=1)

        mock_create.assert_called_once_with("personal")

    def test_permission_denied_read(self) -> None:
        """Test get_email returns error when read is denied."""
        mock_checker = MagicMock(spec=PermissionChecker)
        mock_checker.check_read.side_effect = PermissionDeniedError(
            "Read access denied for this account"
        )

        with patch(
            "read_no_evil_mcp.tools.get_email.get_permission_checker",
            return_value=mock_checker,
        ):
            result = get_email.fn(account="restricted", folder="INBOX", uid=1)

        assert "Permission denied" in result
        assert "Read access denied" in result

    def test_permission_denied_folder(self) -> None:
        """Test get_email returns error when folder access is denied."""
        mock_checker = MagicMock(spec=PermissionChecker)
        mock_checker.check_folder.side_effect = PermissionDeniedError(
            "Access to folder 'Secret' denied"
        )

        with patch(
            "read_no_evil_mcp.tools.get_email.get_permission_checker",
            return_value=mock_checker,
        ):
            result = get_email.fn(account="restricted", folder="Secret", uid=1)

        assert "Permission denied" in result
        assert "folder 'Secret' denied" in result
