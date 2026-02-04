"""Tests for list_folders tool."""

from unittest.mock import MagicMock, patch

import pytest

from read_no_evil_mcp.models import Folder
from read_no_evil_mcp.tools.list_folders import list_folders


class TestListFolders:
    def test_returns_folder_names(self) -> None:
        """Test list_folders tool returns folder names."""
        mock_service = MagicMock()
        mock_service.list_folders.return_value = [
            Folder(name="INBOX"),
            Folder(name="Sent"),
        ]
        mock_service.__enter__ = MagicMock(return_value=mock_service)
        mock_service.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.list_folders.create_securemailbox",
            return_value=mock_service,
        ):
            result = list_folders.fn(account="work")

        assert "INBOX" in result
        assert "Sent" in result

    def test_empty_folders(self) -> None:
        """Test list_folders with no folders."""
        mock_service = MagicMock()
        mock_service.list_folders.return_value = []
        mock_service.__enter__ = MagicMock(return_value=mock_service)
        mock_service.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.list_folders.create_securemailbox",
            return_value=mock_service,
        ):
            result = list_folders.fn(account="work")

        assert "No folders found" in result

    def test_exit_called_on_exception(self) -> None:
        """Test that __exit__ is called even when exception occurs."""
        mock_service = MagicMock()
        mock_service.list_folders.side_effect = RuntimeError("Connection error")
        mock_service.__enter__ = MagicMock(return_value=mock_service)
        mock_service.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.list_folders.create_securemailbox",
            return_value=mock_service,
        ):
            with pytest.raises(RuntimeError):
                list_folders.fn(account="work")

        mock_service.__exit__.assert_called_once()

    def test_passes_account_to_create_securemailbox(self) -> None:
        """Test list_folders passes account to create_securemailbox."""
        mock_service = MagicMock()
        mock_service.list_folders.return_value = []
        mock_service.__enter__ = MagicMock(return_value=mock_service)
        mock_service.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.list_folders.create_securemailbox",
            return_value=mock_service,
        ) as mock_create:
            list_folders.fn(account="personal")

        mock_create.assert_called_once_with("personal")
