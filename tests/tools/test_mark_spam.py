"""Tests for mark_spam tool."""

from unittest.mock import MagicMock, patch

from read_no_evil_mcp.exceptions import PermissionDeniedError
from read_no_evil_mcp.tools.mark_spam import mark_spam


class TestMarkSpam:
    def test_marks_email_as_spam(self) -> None:
        """Test mark_spam tool successfully marks email as spam."""
        mock_mailbox = MagicMock()
        mock_mailbox.mark_spam.return_value = True
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.mark_spam.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = mark_spam.fn(account="work", folder="INBOX", uid=123)

        assert "marked as spam" in result
        assert "INBOX/123" in result
        mock_mailbox.mark_spam.assert_called_once_with("INBOX", 123)

    def test_email_not_found(self) -> None:
        """Test mark_spam with non-existent email."""
        mock_mailbox = MagicMock()
        mock_mailbox.mark_spam.return_value = False
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.mark_spam.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = mark_spam.fn(account="work", folder="INBOX", uid=999)

        assert "not found" in result
        assert "INBOX/999" in result

    def test_permission_denied_mark_spam(self) -> None:
        """Test mark_spam returns error when mark_spam permission is denied."""
        mock_mailbox = MagicMock()
        mock_mailbox.mark_spam.side_effect = PermissionDeniedError(
            "Mark spam access denied for this account"
        )
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.mark_spam.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = mark_spam.fn(account="restricted", folder="INBOX", uid=1)

        assert "Permission denied" in result
        assert "Mark spam access denied" in result

    def test_permission_denied_folder(self) -> None:
        """Test mark_spam returns error when folder access is denied."""
        mock_mailbox = MagicMock()
        mock_mailbox.mark_spam.side_effect = PermissionDeniedError(
            "Access to folder 'Secret' denied"
        )
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.mark_spam.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = mark_spam.fn(account="restricted", folder="Secret", uid=1)

        assert "Permission denied" in result
        assert "folder 'Secret' denied" in result

    def test_passes_account_to_create_securemailbox(self) -> None:
        """Test mark_spam passes account to create_securemailbox."""
        mock_mailbox = MagicMock()
        mock_mailbox.mark_spam.return_value = True
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.mark_spam.create_securemailbox",
            return_value=mock_mailbox,
        ) as mock_create:
            mark_spam.fn(account="personal", folder="INBOX", uid=1)

        mock_create.assert_called_once_with("personal")

    def test_no_spam_folder_error(self) -> None:
        """Test mark_spam returns error when no spam folder exists."""
        mock_mailbox = MagicMock()
        mock_mailbox.mark_spam.side_effect = RuntimeError("No spam folder found")
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.mark_spam.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = mark_spam.fn(account="work", folder="INBOX", uid=1)

        assert "Error" in result
        assert "No spam folder found" in result
