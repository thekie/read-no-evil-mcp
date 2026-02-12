"""Tests for delete_email tool."""

from unittest.mock import MagicMock, patch

from read_no_evil_mcp.exceptions import PermissionDeniedError
from read_no_evil_mcp.tools.delete_email import delete_email


class TestDeleteEmail:
    def test_successfully_deletes_email(self) -> None:
        """Test delete_email tool returns success message."""
        mock_mailbox = MagicMock()
        mock_mailbox.delete_email.return_value = True
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.delete_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = delete_email.fn(account="work", folder="INBOX", uid=123)

        assert "Successfully deleted" in result
        assert "INBOX/123" in result
        mock_mailbox.delete_email.assert_called_once_with("INBOX", 123)

    def test_delete_fails(self) -> None:
        """Test delete_email returns failure message when deletion fails."""
        mock_mailbox = MagicMock()
        mock_mailbox.delete_email.return_value = False
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.delete_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = delete_email.fn(account="work", folder="INBOX", uid=123)

        assert "Failed to delete" in result
        assert "INBOX/123" in result

    def test_passes_account_to_create_securemailbox(self) -> None:
        """Test delete_email passes account to create_securemailbox."""
        mock_mailbox = MagicMock()
        mock_mailbox.delete_email.return_value = True
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.delete_email.create_securemailbox",
            return_value=mock_mailbox,
        ) as mock_create:
            delete_email.fn(account="personal", folder="INBOX", uid=1)

        mock_create.assert_called_once_with("personal")

    def test_permission_denied_delete(self) -> None:
        """Test delete_email returns error when delete is denied."""
        mock_mailbox = MagicMock()
        mock_mailbox.delete_email.side_effect = PermissionDeniedError(
            "Delete access denied for this account"
        )
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.delete_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = delete_email.fn(account="restricted", folder="INBOX", uid=1)

        assert "Permission denied" in result
        assert "Delete access denied" in result

    def test_permission_denied_folder(self) -> None:
        """Test delete_email returns error when folder access is denied."""
        mock_mailbox = MagicMock()
        mock_mailbox.delete_email.side_effect = PermissionDeniedError(
            "Access to folder 'Secret' denied"
        )
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.delete_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = delete_email.fn(account="restricted", folder="Secret", uid=1)

        assert "Permission denied" in result
        assert "folder 'Secret' denied" in result

    def test_different_folder(self) -> None:
        """Test delete_email works with different folders."""
        mock_mailbox = MagicMock()
        mock_mailbox.delete_email.return_value = True
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.delete_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = delete_email.fn(account="work", folder="Sent", uid=456)

        assert "Successfully deleted" in result
        assert "Sent/456" in result
        mock_mailbox.delete_email.assert_called_once_with("Sent", 456)


class TestDeleteEmailValidation:
    def test_uid_zero_rejected(self) -> None:
        result = delete_email.fn(account="work", folder="INBOX", uid=0)
        assert "Invalid parameter" in result
        assert "uid" in result

    def test_uid_negative_rejected(self) -> None:
        result = delete_email.fn(account="work", folder="INBOX", uid=-5)
        assert "Invalid parameter" in result

    def test_empty_folder_rejected(self) -> None:
        result = delete_email.fn(account="work", folder="", uid=1)
        assert "Invalid parameter" in result
        assert "folder" in result

    def test_whitespace_folder_rejected(self) -> None:
        result = delete_email.fn(account="work", folder="  ", uid=1)
        assert "Invalid parameter" in result
