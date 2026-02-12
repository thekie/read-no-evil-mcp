"""Tests for move_email tool."""

from unittest.mock import MagicMock, patch

from read_no_evil_mcp.exceptions import PermissionDeniedError
from read_no_evil_mcp.tools.move_email import move_email


class TestMoveEmail:
    def test_moves_email_to_target_folder(self) -> None:
        """Test move_email tool successfully moves email to target folder."""
        mock_mailbox = MagicMock()
        mock_mailbox.move_email.return_value = True
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.move_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = move_email.fn(account="work", folder="INBOX", uid=123, target_folder="Archive")

        assert "moved to Archive" in result
        assert "INBOX/123" in result
        mock_mailbox.move_email.assert_called_once_with("INBOX", 123, "Archive")

    def test_moves_email_to_spam(self) -> None:
        """Test move_email tool can move email to Spam folder."""
        mock_mailbox = MagicMock()
        mock_mailbox.move_email.return_value = True
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.move_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = move_email.fn(account="work", folder="INBOX", uid=456, target_folder="Spam")

        assert "moved to Spam" in result
        mock_mailbox.move_email.assert_called_once_with("INBOX", 456, "Spam")

    def test_email_not_found(self) -> None:
        """Test move_email with non-existent email."""
        mock_mailbox = MagicMock()
        mock_mailbox.move_email.return_value = False
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.move_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = move_email.fn(account="work", folder="INBOX", uid=999, target_folder="Archive")

        assert "not found" in result
        assert "INBOX/999" in result

    def test_permission_denied_move(self) -> None:
        """Test move_email returns error when move permission is denied."""
        mock_mailbox = MagicMock()
        mock_mailbox.move_email.side_effect = PermissionDeniedError(
            "Move access denied for this account"
        )
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.move_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = move_email.fn(
                account="restricted", folder="INBOX", uid=1, target_folder="Archive"
            )

        assert "Permission denied" in result
        assert "Move access denied" in result

    def test_permission_denied_source_folder(self) -> None:
        """Test move_email returns error when source folder access is denied."""
        mock_mailbox = MagicMock()
        mock_mailbox.move_email.side_effect = PermissionDeniedError(
            "Access to folder 'Secret' denied"
        )
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.move_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = move_email.fn(
                account="restricted", folder="Secret", uid=1, target_folder="Archive"
            )

        assert "Permission denied" in result
        assert "folder 'Secret' denied" in result

    def test_permission_denied_target_folder(self) -> None:
        """Test move_email returns error when target folder access is denied."""
        mock_mailbox = MagicMock()
        mock_mailbox.move_email.side_effect = PermissionDeniedError(
            "Access to folder 'Restricted' denied"
        )
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.move_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = move_email.fn(
                account="work", folder="INBOX", uid=1, target_folder="Restricted"
            )

        assert "Permission denied" in result
        assert "folder 'Restricted' denied" in result

    def test_passes_account_to_create_securemailbox(self) -> None:
        """Test move_email passes account to create_securemailbox."""
        mock_mailbox = MagicMock()
        mock_mailbox.move_email.return_value = True
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.move_email.create_securemailbox",
            return_value=mock_mailbox,
        ) as mock_create:
            move_email.fn(account="personal", folder="INBOX", uid=1, target_folder="Archive")

        mock_create.assert_called_once_with("personal")

    def test_runtime_error(self) -> None:
        """Test move_email returns error on RuntimeError."""
        mock_mailbox = MagicMock()
        mock_mailbox.move_email.side_effect = RuntimeError("Connection lost")
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.move_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = move_email.fn(account="work", folder="INBOX", uid=1, target_folder="Archive")

        assert "Error" in result
        assert "Connection lost" in result


class TestMoveEmailValidation:
    def test_uid_zero_rejected(self) -> None:
        result = move_email.fn(account="work", folder="INBOX", uid=0, target_folder="Archive")
        assert "Invalid parameter" in result
        assert "uid" in result

    def test_empty_folder_rejected(self) -> None:
        result = move_email.fn(account="work", folder="", uid=1, target_folder="Archive")
        assert "Invalid parameter" in result
        assert "folder" in result

    def test_empty_target_folder_rejected(self) -> None:
        result = move_email.fn(account="work", folder="INBOX", uid=1, target_folder="")
        assert "Invalid parameter" in result
        assert "target_folder" in result

    def test_whitespace_target_folder_rejected(self) -> None:
        result = move_email.fn(account="work", folder="INBOX", uid=1, target_folder="   ")
        assert "Invalid parameter" in result
