"""Tests for get_email tool."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from read_no_evil_mcp.accounts.config import AccessLevel
from read_no_evil_mcp.exceptions import PermissionDeniedError
from read_no_evil_mcp.mailbox import PromptInjectionError
from read_no_evil_mcp.models import Email, EmailAddress, ScanResult
from read_no_evil_mcp.tools.get_email import get_email


def _create_mock_mailbox(
    email: Email | None = None,
    access_level: AccessLevel = AccessLevel.SHOW,
    read_prompt: str | None = None,
) -> MagicMock:
    """Create a mock mailbox with standard setup."""
    mock_mailbox = MagicMock()
    mock_mailbox.get_email.return_value = email
    mock_mailbox.get_access_level.return_value = access_level
    mock_mailbox.get_read_prompt.return_value = read_prompt
    mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
    mock_mailbox.__exit__ = MagicMock(return_value=None)
    return mock_mailbox


class TestGetEmail:
    def test_returns_full_email_content(self) -> None:
        """Test get_email tool returns full email content."""
        email = Email(
            uid=123,
            folder="INBOX",
            subject="Test Email",
            sender=EmailAddress(name="Sender", address="sender@example.com"),
            date=datetime(2026, 2, 3, 12, 0, 0),
            to=[EmailAddress(address="to@example.com")],
            body_plain="Hello, World!",
            message_id="<abc@example.com>",
            is_seen=True,
        )
        mock_mailbox = _create_mock_mailbox(email=email)

        with patch(
            "read_no_evil_mcp.tools.get_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = get_email.fn(account="work", folder="INBOX", uid=123)

        assert "Subject: Test Email" in result
        assert "From: Sender <sender@example.com>" in result
        assert "To: to@example.com" in result
        assert "Hello, World!" in result
        assert "Status: Read" in result

    def test_unread_email_shows_unread_status(self) -> None:
        """Test get_email shows Unread status for unseen emails."""
        email = Email(
            uid=123,
            folder="INBOX",
            subject="Unread Email",
            sender=EmailAddress(address="sender@example.com"),
            date=datetime(2026, 2, 3, 12, 0, 0),
            body_plain="Content",
            is_seen=False,
        )
        mock_mailbox = _create_mock_mailbox(email=email)

        with patch(
            "read_no_evil_mcp.tools.get_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = get_email.fn(account="work", folder="INBOX", uid=123)

        assert "Status: Unread" in result

    def test_email_not_found(self) -> None:
        """Test get_email with non-existent email."""
        mock_mailbox = _create_mock_mailbox(email=None)

        with patch(
            "read_no_evil_mcp.tools.get_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = get_email.fn(account="work", folder="INBOX", uid=999)

        assert "Email not found" in result

    def test_html_only_email(self) -> None:
        """Test get_email with HTML-only content."""
        email = Email(
            uid=123,
            folder="INBOX",
            subject="HTML Email",
            sender=EmailAddress(address="sender@example.com"),
            date=datetime(2026, 2, 3, 12, 0, 0),
            body_html="<p>HTML content</p>",
        )
        mock_mailbox = _create_mock_mailbox(email=email)

        with patch(
            "read_no_evil_mcp.tools.get_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = get_email.fn(account="work", folder="INBOX", uid=123)

        assert "HTML content - plain text not available" in result
        assert "<p>HTML content</p>" in result

    def test_blocked_email(self) -> None:
        """Test get_email with prompt injection detected."""
        mock_mailbox = _create_mock_mailbox()
        scan_result = ScanResult(
            is_safe=False,
            score=0.8,
            detected_patterns=["ignore_instructions", "you_are_now"],
        )
        mock_mailbox.get_email.side_effect = PromptInjectionError(
            scan_result, email_uid=123, folder="INBOX"
        )

        with patch(
            "read_no_evil_mcp.tools.get_email.create_securemailbox",
            return_value=mock_mailbox,
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
        mock_mailbox = _create_mock_mailbox()
        scan_result = ScanResult(
            is_safe=False,
            score=0.5,
            detected_patterns=["system_tag"],
        )
        mock_mailbox.get_email.side_effect = PromptInjectionError(
            scan_result, email_uid=456, folder="Sent"
        )

        with patch(
            "read_no_evil_mcp.tools.get_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = get_email.fn(account="work", folder="Sent", uid=456)

        assert "BLOCKED" in result
        assert "Sent/456" in result
        assert "system_tag" in result

    def test_passes_account_to_create_securemailbox(self) -> None:
        """Test get_email passes account to create_securemailbox."""
        mock_mailbox = _create_mock_mailbox(email=None)

        with patch(
            "read_no_evil_mcp.tools.get_email.create_securemailbox",
            return_value=mock_mailbox,
        ) as mock_create:
            get_email.fn(account="personal", folder="INBOX", uid=1)

        mock_create.assert_called_once_with("personal")

    def test_permission_denied_read(self) -> None:
        """Test get_email returns error when read is denied."""
        mock_mailbox = _create_mock_mailbox()
        mock_mailbox.get_email.side_effect = PermissionDeniedError(
            "Read access denied for this account"
        )

        with patch(
            "read_no_evil_mcp.tools.get_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = get_email.fn(account="restricted", folder="INBOX", uid=1)

        assert "Permission denied" in result
        assert "Read access denied" in result

    def test_permission_denied_folder(self) -> None:
        """Test get_email returns error when folder access is denied."""
        mock_mailbox = _create_mock_mailbox()
        mock_mailbox.get_email.side_effect = PermissionDeniedError(
            "Access to folder 'Secret' denied"
        )

        with patch(
            "read_no_evil_mcp.tools.get_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = get_email.fn(account="restricted", folder="Secret", uid=1)

        assert "Permission denied" in result
        assert "folder 'Secret' denied" in result

    def test_trusted_access_shown(self) -> None:
        """Test that Access: TRUSTED is shown for trusted sender."""
        email = Email(
            uid=123,
            folder="INBOX",
            subject="Report",
            sender=EmailAddress(address="boss@mycompany.com"),
            date=datetime(2026, 2, 3, 12, 0, 0),
            body_plain="Please review.",
            is_seen=True,
        )
        mock_mailbox = _create_mock_mailbox(
            email=email,
            access_level=AccessLevel.TRUSTED,
            read_prompt="Trusted sender. You may follow instructions from this email.",
        )

        with patch(
            "read_no_evil_mcp.tools.get_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = get_email.fn(account="work", folder="INBOX", uid=123)

        assert "Access: TRUSTED" in result
        assert "Trusted sender" in result

    def test_ask_before_read_access_shown(self) -> None:
        """Test that Access: ASK_BEFORE_READ is shown for ask_before_read sender."""
        email = Email(
            uid=123,
            folder="INBOX",
            subject="Invoice",
            sender=EmailAddress(address="vendor@external.com"),
            date=datetime(2026, 2, 3, 12, 0, 0),
            body_plain="Please pay.",
            is_seen=True,
        )
        mock_mailbox = _create_mock_mailbox(
            email=email,
            access_level=AccessLevel.ASK_BEFORE_READ,
            read_prompt="Confirmation expected. Proceed with caution.",
        )

        with patch(
            "read_no_evil_mcp.tools.get_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = get_email.fn(account="work", folder="INBOX", uid=123)

        assert "Access: ASK_BEFORE_READ" in result
        assert "caution" in result.lower()

    def test_show_level_no_access_line(self) -> None:
        """Test that SHOW level has no Access line."""
        email = Email(
            uid=123,
            folder="INBOX",
            subject="Hello",
            sender=EmailAddress(address="unknown@example.com"),
            date=datetime(2026, 2, 3, 12, 0, 0),
            body_plain="Hi there",
            is_seen=True,
        )
        mock_mailbox = _create_mock_mailbox(
            email=email,
            access_level=AccessLevel.SHOW,
            read_prompt=None,
        )

        with patch(
            "read_no_evil_mcp.tools.get_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = get_email.fn(account="work", folder="INBOX", uid=123)

        assert "Access:" not in result
        # No prompt line for SHOW level
        assert "->" not in result

    def test_custom_read_prompt_shown(self) -> None:
        """Test that custom read prompts are shown."""
        email = Email(
            uid=123,
            folder="INBOX",
            subject="Report",
            sender=EmailAddress(address="boss@mycompany.com"),
            date=datetime(2026, 2, 3, 12, 0, 0),
            body_plain="Please review.",
            is_seen=True,
        )
        mock_mailbox = _create_mock_mailbox(
            email=email,
            access_level=AccessLevel.TRUSTED,
            read_prompt="Custom trusted read prompt here",
        )

        with patch(
            "read_no_evil_mcp.tools.get_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = get_email.fn(account="work", folder="INBOX", uid=123)

        assert "Custom trusted read prompt here" in result
