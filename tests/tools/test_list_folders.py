"""Tests for list_folders tool."""

from unittest.mock import MagicMock, patch

import pytest

from read_no_evil_mcp.models import Folder
from read_no_evil_mcp.tools.list_folders import list_folders_impl


class TestListFolders:
    def test_returns_folder_names(self) -> None:
        """Test list_folders tool returns folder names."""
        mock_service = MagicMock()
        mock_service.list_folders.return_value = [
            Folder(name="INBOX"),
            Folder(name="Sent"),
        ]

        with patch(
            "read_no_evil_mcp.tools.list_folders.create_service",
            return_value=mock_service,
        ):
            result = list_folders_impl()

        assert "INBOX" in result
        assert "Sent" in result
        mock_service.connect.assert_called_once()
        mock_service.disconnect.assert_called_once()

    def test_empty_folders(self) -> None:
        """Test list_folders with no folders."""
        mock_service = MagicMock()
        mock_service.list_folders.return_value = []

        with patch(
            "read_no_evil_mcp.tools.list_folders.create_service",
            return_value=mock_service,
        ):
            result = list_folders_impl()

        assert "No folders found" in result

    def test_disconnect_called_on_exception(self) -> None:
        """Test that disconnect is called even when exception occurs."""
        mock_service = MagicMock()
        mock_service.list_folders.side_effect = RuntimeError("Connection error")

        with patch(
            "read_no_evil_mcp.tools.list_folders.create_service",
            return_value=mock_service,
        ):
            with pytest.raises(RuntimeError):
                list_folders_impl()

        mock_service.disconnect.assert_called_once()
