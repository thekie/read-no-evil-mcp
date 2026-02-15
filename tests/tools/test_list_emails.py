"""Tests for list_emails tool."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from read_no_evil_mcp.accounts.config import AccessLevel
from read_no_evil_mcp.exceptions import PermissionDeniedError
from read_no_evil_mcp.mailbox import SecureEmailSummary
from read_no_evil_mcp.models import EmailAddress, EmailSummary
from read_no_evil_mcp.tools.list_emails import list_emails


def _create_secure_summary(
    uid: int = 1,
    subject: str = "Test Subject",
    sender: str = "sender@example.com",
    access_level: AccessLevel = AccessLevel.SHOW,
    prompt: str | None = None,
    has_attachments: bool = False,
    is_seen: bool = True,
) -> SecureEmailSummary:
    """Create a SecureEmailSummary for testing."""
    summary = EmailSummary(
        uid=uid,
        folder="INBOX",
        subject=subject,
        sender=EmailAddress(address=sender),
        date=datetime(2026, 2, 3, 12, 0, 0),
        has_attachments=has_attachments,
        is_seen=is_seen,
    )
    return SecureEmailSummary(
        summary=summary,
        access_level=access_level,
        prompt=prompt,
    )


def _create_mock_mailbox(
    secure_emails: list[SecureEmailSummary] | None = None,
) -> MagicMock:
    """Create a mock mailbox with standard setup."""
    mock_mailbox = MagicMock()
    mock_mailbox.fetch_emails.return_value = secure_emails or []
    mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
    mock_mailbox.__exit__ = MagicMock(return_value=None)
    return mock_mailbox


class TestListEmails:
    def test_returns_email_summaries(self) -> None:
        """Test list_emails tool returns email summaries."""
        secure_emails = [
            _create_secure_summary(uid=1, subject="Test Subject", has_attachments=True)
        ]
        mock_mailbox = _create_mock_mailbox(secure_emails=secure_emails)

        with patch(
            "read_no_evil_mcp.tools.list_emails.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = list_emails.fn(account="work", folder="INBOX", days_back=7)

        assert result == "[1] 2026-02-03 12:00 | sender@example.com | Test Subject [+]"

    def test_unseen_email_shows_unread_marker(self) -> None:
        """Test list_emails shows [UNREAD] marker for unseen emails."""
        secure_emails = [_create_secure_summary(subject="Unread Email", is_seen=False)]
        mock_mailbox = _create_mock_mailbox(secure_emails=secure_emails)

        with patch(
            "read_no_evil_mcp.tools.list_emails.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = list_emails.fn(account="work")

        assert result == "[1] 2026-02-03 12:00 | sender@example.com | Unread Email [UNREAD]"

    def test_no_emails(self) -> None:
        """Test list_emails with no emails."""
        mock_mailbox = _create_mock_mailbox(secure_emails=[])

        with patch(
            "read_no_evil_mcp.tools.list_emails.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = list_emails.fn(account="work")

        assert result == "No emails found."

    def test_respects_limit_parameter(self) -> None:
        """Test list_emails respects limit parameter."""
        mock_mailbox = _create_mock_mailbox(secure_emails=[])

        with patch(
            "read_no_evil_mcp.tools.list_emails.create_securemailbox",
            return_value=mock_mailbox,
        ):
            list_emails.fn(account="work", folder="INBOX", limit=5)

        call_args = mock_mailbox.fetch_emails.call_args
        assert call_args.kwargs["limit"] == 5

    def test_default_parameters(self) -> None:
        """Test list_emails uses default parameters."""
        mock_mailbox = _create_mock_mailbox(secure_emails=[])

        with patch(
            "read_no_evil_mcp.tools.list_emails.create_securemailbox",
            return_value=mock_mailbox,
        ):
            list_emails.fn(account="work")

        call_args = mock_mailbox.fetch_emails.call_args
        assert call_args.args[0] == "INBOX"

    def test_passes_account_to_create_securemailbox(self) -> None:
        """Test list_emails passes account to create_securemailbox."""
        mock_mailbox = _create_mock_mailbox(secure_emails=[])

        with patch(
            "read_no_evil_mcp.tools.list_emails.create_securemailbox",
            return_value=mock_mailbox,
        ) as mock_create:
            list_emails.fn(account="personal")

        mock_create.assert_called_once_with("personal")

    def test_permission_denied_read(self) -> None:
        """Test list_emails returns error when read is denied."""
        mock_mailbox = _create_mock_mailbox()
        mock_mailbox.fetch_emails.side_effect = PermissionDeniedError(
            "Read access denied for this account"
        )

        with patch(
            "read_no_evil_mcp.tools.list_emails.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = list_emails.fn(account="restricted")

        assert result == "Permission denied: Read access denied for this account"

    def test_permission_denied_folder(self) -> None:
        """Test list_emails returns error when folder access is denied."""
        mock_mailbox = _create_mock_mailbox()
        mock_mailbox.fetch_emails.side_effect = PermissionDeniedError(
            "Access to folder 'Drafts' denied"
        )

        with patch(
            "read_no_evil_mcp.tools.list_emails.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = list_emails.fn(account="restricted", folder="Drafts")

        assert result == "Permission denied: Access to folder 'Drafts' denied"

    def test_trusted_marker_shown(self) -> None:
        """Test that [TRUSTED] marker is shown for trusted sender."""
        secure_emails = [
            _create_secure_summary(
                subject="Report",
                sender="boss@mycompany.com",
                access_level=AccessLevel.TRUSTED,
                prompt="Trusted sender. Read and process directly.",
            )
        ]
        mock_mailbox = _create_mock_mailbox(secure_emails=secure_emails)

        with patch(
            "read_no_evil_mcp.tools.list_emails.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = list_emails.fn(account="work")

        lines = result.split("\n")
        assert lines[0].endswith("[TRUSTED]")
        assert lines[1] == "    -> Trusted sender. Read and process directly."

    def test_ask_marker_shown(self) -> None:
        """Test that [ASK] marker is shown for ask_before_read sender."""
        secure_emails = [
            _create_secure_summary(
                subject="Invoice",
                sender="vendor@external.com",
                access_level=AccessLevel.ASK_BEFORE_READ,
                prompt="Ask user for permission before reading.",
            )
        ]
        mock_mailbox = _create_mock_mailbox(secure_emails=secure_emails)

        with patch(
            "read_no_evil_mcp.tools.list_emails.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = list_emails.fn(account="work")

        lines = result.split("\n")
        assert lines[0].endswith("[ASK]")
        assert lines[1] == "    -> Ask user for permission before reading."

    def test_show_level_no_marker(self) -> None:
        """Test that SHOW level has no marker."""
        secure_emails = [
            _create_secure_summary(
                subject="Hello",
                sender="unknown@example.com",
                access_level=AccessLevel.SHOW,
                prompt=None,
            )
        ]
        mock_mailbox = _create_mock_mailbox(secure_emails=secure_emails)

        with patch(
            "read_no_evil_mcp.tools.list_emails.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = list_emails.fn(account="work")

        assert result == "[1] 2026-02-03 12:00 | unknown@example.com | Hello"

    def test_custom_prompt_shown(self) -> None:
        """Test that custom prompts are shown."""
        secure_emails = [
            _create_secure_summary(
                subject="Report",
                sender="boss@mycompany.com",
                access_level=AccessLevel.TRUSTED,
                prompt="Custom trusted message here",
            )
        ]
        mock_mailbox = _create_mock_mailbox(secure_emails=secure_emails)

        with patch(
            "read_no_evil_mcp.tools.list_emails.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = list_emails.fn(account="work")

        lines = result.split("\n")
        assert len(lines) == 2
        assert lines[1] == "    -> Custom trusted message here"

    def test_subject_rule_matching(self) -> None:
        """Test subject rule matching for access level."""
        secure_emails = [
            _create_secure_summary(
                subject="[URGENT] Action Required",
                sender="unknown@example.com",
                access_level=AccessLevel.ASK_BEFORE_READ,
                prompt="Ask user for permission before reading.",
            )
        ]
        mock_mailbox = _create_mock_mailbox(secure_emails=secure_emails)

        with patch(
            "read_no_evil_mcp.tools.list_emails.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = list_emails.fn(account="work")

        lines = result.split("\n")
        assert "[URGENT] Action Required [ASK]" in lines[0]
        assert lines[1] == "    -> Ask user for permission before reading."


class TestListEmailsValidation:
    def test_days_back_zero_rejected(self) -> None:
        result = list_emails.fn(account="work", days_back=0)
        assert result == "Invalid parameter: days_back must be a positive integer"

    def test_days_back_negative_rejected(self) -> None:
        result = list_emails.fn(account="work", days_back=-1)
        assert result == "Invalid parameter: days_back must be a positive integer"

    def test_empty_folder_rejected(self) -> None:
        result = list_emails.fn(account="work", folder="")
        assert result == "Invalid parameter: folder must not be empty"

    def test_whitespace_folder_rejected(self) -> None:
        result = list_emails.fn(account="work", folder="  ")
        assert result == "Invalid parameter: folder must not be empty"

    def test_limit_zero_rejected(self) -> None:
        result = list_emails.fn(account="work", limit=0)
        assert result == "Invalid parameter: limit must be a positive integer"

    def test_limit_negative_rejected(self) -> None:
        result = list_emails.fn(account="work", limit=-3)
        assert result == "Invalid parameter: limit must be a positive integer"
