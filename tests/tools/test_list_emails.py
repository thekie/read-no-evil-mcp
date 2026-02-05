"""Tests for list_emails tool."""

from datetime import datetime
from unittest.mock import MagicMock, patch

from read_no_evil_mcp.exceptions import PermissionDeniedError
from read_no_evil_mcp.models import EmailAddress, EmailSummary
from read_no_evil_mcp.tools.list_emails import list_emails


class TestListEmails:
    def test_returns_email_summaries(self) -> None:
        """Test list_emails tool returns email summaries."""
        mock_mailbox = MagicMock()
        mock_mailbox.fetch_emails.return_value = [
            EmailSummary(
                uid=1,
                folder="INBOX",
                subject="Test Subject",
                sender=EmailAddress(address="sender@example.com"),
                date=datetime(2026, 2, 3, 12, 0, 0),
                has_attachments=True,
                is_seen=True,
            ),
        ]
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.list_emails.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = list_emails.fn(account="work", folder="INBOX", days_back=7)

        assert "[1]" in result
        assert "Test Subject" in result
        assert "sender@example.com" in result
        assert "[+]" in result  # attachment marker
        assert "[NEW]" not in result  # seen email should not have NEW marker

    def test_unseen_email_shows_new_marker(self) -> None:
        """Test list_emails shows [NEW] marker for unseen emails."""
        mock_mailbox = MagicMock()
        mock_mailbox.fetch_emails.return_value = [
            EmailSummary(
                uid=1,
                folder="INBOX",
                subject="Unread Email",
                sender=EmailAddress(address="sender@example.com"),
                date=datetime(2026, 2, 3, 12, 0, 0),
                is_seen=False,
            ),
        ]
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.list_emails.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = list_emails.fn(account="work")

        assert "[NEW]" in result

    def test_no_emails(self) -> None:
        """Test list_emails with no emails."""
        mock_mailbox = MagicMock()
        mock_mailbox.fetch_emails.return_value = []
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.list_emails.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = list_emails.fn(account="work")

        assert "No emails found" in result

    def test_respects_limit_parameter(self) -> None:
        """Test list_emails respects limit parameter."""
        mock_mailbox = MagicMock()
        mock_mailbox.fetch_emails.return_value = []
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.list_emails.create_securemailbox",
            return_value=mock_mailbox,
        ):
            list_emails.fn(account="work", folder="INBOX", limit=5)

        call_args = mock_mailbox.fetch_emails.call_args
        assert call_args.kwargs["limit"] == 5

    def test_default_parameters(self) -> None:
        """Test list_emails uses default parameters."""
        mock_mailbox = MagicMock()
        mock_mailbox.fetch_emails.return_value = []
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.list_emails.create_securemailbox",
            return_value=mock_mailbox,
        ):
            list_emails.fn(account="work")

        call_args = mock_mailbox.fetch_emails.call_args
        assert call_args.args[0] == "INBOX"

    def test_passes_account_to_create_securemailbox(self) -> None:
        """Test list_emails passes account to create_securemailbox."""
        mock_mailbox = MagicMock()
        mock_mailbox.fetch_emails.return_value = []
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.list_emails.create_securemailbox",
            return_value=mock_mailbox,
        ) as mock_create:
            list_emails.fn(account="personal")

        mock_create.assert_called_once_with("personal")

    def test_permission_denied_read(self) -> None:
        """Test list_emails returns error when read is denied."""
        mock_mailbox = MagicMock()
        mock_mailbox.fetch_emails.side_effect = PermissionDeniedError(
            "Read access denied for this account"
        )
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.list_emails.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = list_emails.fn(account="restricted")

        assert "Permission denied" in result
        assert "Read access denied" in result

    def test_permission_denied_folder(self) -> None:
        """Test list_emails returns error when folder access is denied."""
        mock_mailbox = MagicMock()
        mock_mailbox.fetch_emails.side_effect = PermissionDeniedError(
            "Access to folder 'Drafts' denied"
        )
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.list_emails.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = list_emails.fn(account="restricted", folder="Drafts")

        assert "Permission denied" in result
        assert "folder 'Drafts' denied" in result
