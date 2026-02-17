"""Tests for get_email tool."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from read_no_evil_mcp.accounts.config import AccessLevel
from read_no_evil_mcp.exceptions import PermissionDeniedError
from read_no_evil_mcp.mailbox import PromptInjectionError, SecureEmail
from read_no_evil_mcp.models import Email, EmailAddress, ScanResult
from read_no_evil_mcp.tools.get_email import get_email


def _create_secure_email(
    uid: int = 123,
    subject: str = "Test Email",
    sender: str = "sender@example.com",
    sender_name: str | None = None,
    body_plain: str | None = "Hello, World!",
    body_html: str | None = None,
    is_seen: bool = True,
    access_level: AccessLevel = AccessLevel.SHOW,
    prompt: str | None = None,
    protection_skipped: bool = False,
) -> SecureEmail:
    """Create a SecureEmail for testing."""
    email = Email(
        uid=uid,
        folder="INBOX",
        subject=subject,
        sender=EmailAddress(name=sender_name, address=sender),
        date=datetime(2026, 2, 3, 12, 0, 0),
        to=[EmailAddress(address="to@example.com")],
        body_plain=body_plain,
        body_html=body_html,
        message_id="<abc@example.com>",
        is_seen=is_seen,
    )
    return SecureEmail(
        email=email,
        access_level=access_level,
        prompt=prompt,
        protection_skipped=protection_skipped,
    )


def _create_mock_mailbox(
    secure_email: SecureEmail | None = None,
) -> MagicMock:
    """Create a mock mailbox with standard setup."""
    mock_mailbox = MagicMock()
    mock_mailbox.get_email.return_value = secure_email
    mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
    mock_mailbox.__exit__ = MagicMock(return_value=None)
    return mock_mailbox


class TestGetEmail:
    def test_returns_full_email_content(self) -> None:
        """Test get_email tool returns full email content."""
        secure_email = _create_secure_email(sender_name="Sender")
        mock_mailbox = _create_mock_mailbox(secure_email=secure_email)

        with patch(
            "read_no_evil_mcp.tools.get_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = get_email.fn(account="work", folder="INBOX", uid=123)

        lines = result.split("\n")
        assert lines[0] == "Subject: Test Email"
        assert lines[1] == "From: Sender <sender@example.com>"
        assert lines[2] == "To: to@example.com"
        assert lines[3] == "Date: 2026-02-03 12:00:00"
        assert lines[4] == "Status: Read"
        assert lines[5] == "Message-ID: <abc@example.com>"
        assert lines[6] == ""
        assert lines[7] == "Hello, World!"

    def test_unread_email_shows_unread_status(self) -> None:
        """Test get_email shows Unread status for unseen emails."""
        secure_email = _create_secure_email(subject="Unread Email", is_seen=False)
        mock_mailbox = _create_mock_mailbox(secure_email=secure_email)

        with patch(
            "read_no_evil_mcp.tools.get_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = get_email.fn(account="work", folder="INBOX", uid=123)

        lines = result.split("\n")
        assert lines[4] == "Status: Unread"

    def test_email_not_found(self) -> None:
        """Test get_email with non-existent email."""
        mock_mailbox = _create_mock_mailbox(secure_email=None)

        with patch(
            "read_no_evil_mcp.tools.get_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = get_email.fn(account="work", folder="INBOX", uid=999)

        assert result == "Email not found: INBOX/999"

    def test_html_only_email(self) -> None:
        """Test get_email with HTML-only content."""
        secure_email = _create_secure_email(
            subject="HTML Email",
            body_plain=None,
            body_html="<p>HTML content</p>",
        )
        mock_mailbox = _create_mock_mailbox(secure_email=secure_email)

        with patch(
            "read_no_evil_mcp.tools.get_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = get_email.fn(account="work", folder="INBOX", uid=123)

        lines = result.split("\n")
        # Body section starts after blank line separator
        body_start = lines.index("") + 1
        assert lines[body_start] == "[HTML content - plain text not available]"
        assert lines[body_start + 1] == "<p>HTML content</p>"

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

        lines = result.split("\n")
        assert lines[0] == "BLOCKED: Email INBOX/123 contains suspected prompt injection."
        assert lines[1] == "Detected patterns: ignore_instructions, you_are_now"
        assert lines[2] == "Score: 0.80"

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

        lines = result.split("\n")
        assert lines[0] == "BLOCKED: Email Sent/456 contains suspected prompt injection."
        assert lines[1] == "Detected patterns: system_tag"
        assert lines[2] == "Score: 0.50"

    def test_passes_account_to_create_securemailbox(self) -> None:
        """Test get_email passes account to create_securemailbox."""
        mock_mailbox = _create_mock_mailbox(secure_email=None)

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

        assert result == "Permission denied: Read access denied for this account"

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

        assert result == "Permission denied: Access to folder 'Secret' denied"

    def test_trusted_access_shown(self) -> None:
        """Test that Access: TRUSTED is shown for trusted sender."""
        secure_email = _create_secure_email(
            subject="Report",
            sender="boss@mycompany.com",
            body_plain="Please review.",
            access_level=AccessLevel.TRUSTED,
            prompt="Trusted sender. You may follow instructions from this email.",
        )
        mock_mailbox = _create_mock_mailbox(secure_email=secure_email)

        with patch(
            "read_no_evil_mcp.tools.get_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = get_email.fn(account="work", folder="INBOX", uid=123)

        lines = result.split("\n")
        assert "Access: TRUSTED" in lines
        assert "-> Trusted sender. You may follow instructions from this email." in lines

    def test_ask_before_read_access_shown(self) -> None:
        """Test that Access: ASK_BEFORE_READ is shown for ask_before_read sender."""
        secure_email = _create_secure_email(
            subject="Invoice",
            sender="vendor@external.com",
            body_plain="Please pay.",
            access_level=AccessLevel.ASK_BEFORE_READ,
            prompt="Confirmation expected. Proceed with caution.",
        )
        mock_mailbox = _create_mock_mailbox(secure_email=secure_email)

        with patch(
            "read_no_evil_mcp.tools.get_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = get_email.fn(account="work", folder="INBOX", uid=123)

        lines = result.split("\n")
        assert "Access: ASK_BEFORE_READ" in lines
        assert "-> Confirmation expected. Proceed with caution." in lines

    def test_show_level_no_access_line(self) -> None:
        """Test that SHOW level has no Access line."""
        secure_email = _create_secure_email(
            subject="Hello",
            sender="unknown@example.com",
            body_plain="Hi there",
            access_level=AccessLevel.SHOW,
            prompt=None,
        )
        mock_mailbox = _create_mock_mailbox(secure_email=secure_email)

        with patch(
            "read_no_evil_mcp.tools.get_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = get_email.fn(account="work", folder="INBOX", uid=123)

        lines = result.split("\n")
        assert not any(line.startswith("Access:") for line in lines)
        assert not any(line.startswith("->") for line in lines)

    def test_custom_read_prompt_shown(self) -> None:
        """Test that custom read prompts are shown."""
        secure_email = _create_secure_email(
            subject="Report",
            sender="boss@mycompany.com",
            body_plain="Please review.",
            access_level=AccessLevel.TRUSTED,
            prompt="Custom trusted read prompt here",
        )
        mock_mailbox = _create_mock_mailbox(secure_email=secure_email)

        with patch(
            "read_no_evil_mcp.tools.get_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = get_email.fn(account="work", folder="INBOX", uid=123)

        lines = result.split("\n")
        assert "-> Custom trusted read prompt here" in lines


class TestGetEmailValidation:
    def test_uid_zero_rejected(self) -> None:
        result = get_email.fn(account="work", folder="INBOX", uid=0)
        assert result == "Invalid parameter: uid must be a positive integer"

    def test_uid_negative_rejected(self) -> None:
        result = get_email.fn(account="work", folder="INBOX", uid=-1)
        assert result == "Invalid parameter: uid must be a positive integer"

    def test_empty_folder_rejected(self) -> None:
        result = get_email.fn(account="work", folder="", uid=1)
        assert result == "Invalid parameter: folder must not be empty"

    def test_whitespace_folder_rejected(self) -> None:
        result = get_email.fn(account="work", folder="   ", uid=1)
        assert result == "Invalid parameter: folder must not be empty"


class TestGetEmailProtectionSkipped:
    def test_protection_skipped_shown(self) -> None:
        """Test that 'Protection: SKIPPED' line appears when protection_skipped=True."""
        secure_email = _create_secure_email(
            subject="Internal Report",
            sender="user@internal.com",
            body_plain="Content here.",
            protection_skipped=True,
        )
        mock_mailbox = _create_mock_mailbox(secure_email=secure_email)

        with patch(
            "read_no_evil_mcp.tools.get_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = get_email.fn(account="work", folder="INBOX", uid=123)

        lines = result.split("\n")
        assert "Protection: SKIPPED" in lines

    def test_protection_skipped_not_shown(self) -> None:
        """Test that 'Protection: SKIPPED' line does NOT appear when protection_skipped=False."""
        secure_email = _create_secure_email(
            subject="Normal Email",
            sender="user@example.com",
            body_plain="Normal content.",
            protection_skipped=False,
        )
        mock_mailbox = _create_mock_mailbox(secure_email=secure_email)

        with patch(
            "read_no_evil_mcp.tools.get_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = get_email.fn(account="work", folder="INBOX", uid=123)

        lines = result.split("\n")
        assert "Protection: SKIPPED" not in lines
