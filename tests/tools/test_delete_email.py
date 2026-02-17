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
            result = delete_email.fn(account="work", folder="INBOX", uid="123")

        assert result == "Successfully deleted email INBOX/123"
        mock_mailbox.delete_email.assert_called_once_with("INBOX", "123")

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
            result = delete_email.fn(account="work", folder="INBOX", uid="123")

        assert result == "Failed to delete email INBOX/123"

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
            delete_email.fn(account="personal", folder="INBOX", uid="1")

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
            result = delete_email.fn(account="restricted", folder="INBOX", uid="1")

        assert result == "Permission denied: Delete access denied for this account"

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
            result = delete_email.fn(account="restricted", folder="Secret", uid="1")

        assert result == "Permission denied: Access to folder 'Secret' denied"

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
            result = delete_email.fn(account="work", folder="Sent", uid="456")

        assert result == "Successfully deleted email Sent/456"
        mock_mailbox.delete_email.assert_called_once_with("Sent", "456")


class TestDeleteEmailValidation:
    def test_empty_uid_rejected(self) -> None:
        result = delete_email.fn(account="work", folder="INBOX", uid="")
        assert result == "Invalid parameter: uid must not be empty"

    def test_whitespace_uid_rejected(self) -> None:
        result = delete_email.fn(account="work", folder="INBOX", uid="   ")
        assert result == "Invalid parameter: uid must not be empty"

    def test_empty_folder_rejected(self) -> None:
        result = delete_email.fn(account="work", folder="", uid="1")
        assert result == "Invalid parameter: folder must not be empty"

    def test_whitespace_folder_rejected(self) -> None:
        result = delete_email.fn(account="work", folder="  ", uid="1")
        assert result == "Invalid parameter: folder must not be empty"
