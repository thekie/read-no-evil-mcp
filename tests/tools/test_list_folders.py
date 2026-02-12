"""Tests for list_folders tool."""

from unittest.mock import MagicMock, patch

from read_no_evil_mcp.exceptions import PermissionDeniedError
from read_no_evil_mcp.models import Folder
from read_no_evil_mcp.tools.list_folders import list_folders


class TestListFolders:
    def test_returns_folder_names(self) -> None:
        """Test list_folders tool returns folder names."""
        mock_mailbox = MagicMock()
        mock_mailbox.list_folders.return_value = [
            Folder(name="INBOX"),
            Folder(name="Sent"),
        ]
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.list_folders.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = list_folders.fn(account="work")

        assert "INBOX" in result
        assert "Sent" in result

    def test_empty_folders(self) -> None:
        """Test list_folders with no folders."""
        mock_mailbox = MagicMock()
        mock_mailbox.list_folders.return_value = []
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.list_folders.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = list_folders.fn(account="work")

        assert "No folders found" in result

    def test_runtime_error_returns_message(self) -> None:
        """Test that RuntimeError is caught and returned as user-friendly message."""
        mock_mailbox = MagicMock()
        mock_mailbox.list_folders.side_effect = RuntimeError("Connection error")
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.list_folders.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = list_folders.fn(account="work")

        assert "Error" in result
        assert "Connection error" in result
        mock_mailbox.__exit__.assert_called_once()

    def test_passes_account_to_create_securemailbox(self) -> None:
        """Test list_folders passes account to create_securemailbox."""
        mock_mailbox = MagicMock()
        mock_mailbox.list_folders.return_value = []
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.list_folders.create_securemailbox",
            return_value=mock_mailbox,
        ) as mock_create:
            list_folders.fn(account="personal")

        mock_create.assert_called_once_with("personal")

    def test_permission_denied_read(self) -> None:
        """Test list_folders returns error when read is denied."""
        mock_mailbox = MagicMock()
        mock_mailbox.list_folders.side_effect = PermissionDeniedError(
            "Read access denied for this account"
        )
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.list_folders.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = list_folders.fn(account="restricted")

        assert "Permission denied" in result
        assert "Read access denied" in result
