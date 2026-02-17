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
            result = move_email.fn(
                account="work", folder="INBOX", uid="123", target_folder="Archive"
            )

        assert result == "Email INBOX/123 moved to Archive."
        mock_mailbox.move_email.assert_called_once_with("INBOX", "123", "Archive")

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
            result = move_email.fn(account="work", folder="INBOX", uid="456", target_folder="Spam")

        assert result == "Email INBOX/456 moved to Spam."
        mock_mailbox.move_email.assert_called_once_with("INBOX", "456", "Spam")

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
            result = move_email.fn(
                account="work", folder="INBOX", uid="999", target_folder="Archive"
            )

        assert result == "Email not found: INBOX/999"

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
                account="restricted", folder="INBOX", uid="1", target_folder="Archive"
            )

        assert result == "Permission denied: Move access denied for this account"

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
                account="restricted", folder="Secret", uid="1", target_folder="Archive"
            )

        assert result == "Permission denied: Access to folder 'Secret' denied"

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
                account="work", folder="INBOX", uid="1", target_folder="Restricted"
            )

        assert result == "Permission denied: Access to folder 'Restricted' denied"

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
            move_email.fn(account="personal", folder="INBOX", uid="1", target_folder="Archive")

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
            result = move_email.fn(account="work", folder="INBOX", uid="1", target_folder="Archive")

        assert result == "Error: Connection lost"


class TestMoveEmailValidation:
    def test_empty_uid_rejected(self) -> None:
        result = move_email.fn(account="work", folder="INBOX", uid="", target_folder="Archive")
        assert result == "Invalid parameter: uid must not be empty"

    def test_whitespace_uid_rejected(self) -> None:
        result = move_email.fn(account="work", folder="INBOX", uid="   ", target_folder="Archive")
        assert result == "Invalid parameter: uid must not be empty"

    def test_empty_folder_rejected(self) -> None:
        result = move_email.fn(account="work", folder="", uid="1", target_folder="Archive")
        assert result == "Invalid parameter: folder must not be empty"

    def test_empty_target_folder_rejected(self) -> None:
        result = move_email.fn(account="work", folder="INBOX", uid="1", target_folder="")
        assert result == "Invalid parameter: target_folder must not be empty"

    def test_whitespace_target_folder_rejected(self) -> None:
        result = move_email.fn(account="work", folder="INBOX", uid="1", target_folder="   ")
        assert result == "Invalid parameter: target_folder must not be empty"
