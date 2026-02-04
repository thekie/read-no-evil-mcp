"""Tests for list_accounts tool."""

from unittest.mock import patch

from read_no_evil_mcp.tools.list_accounts import list_accounts


class TestListAccounts:
    def test_returns_account_list(self) -> None:
        """Test list_accounts tool returns account IDs."""
        with patch(
            "read_no_evil_mcp.tools.list_accounts.list_configured_accounts",
            return_value=["work", "personal"],
        ):
            result = list_accounts.fn()

        assert "work" in result
        assert "personal" in result

    def test_no_accounts(self) -> None:
        """Test list_accounts with no accounts configured."""
        with patch(
            "read_no_evil_mcp.tools.list_accounts.list_configured_accounts",
            return_value=[],
        ):
            result = list_accounts.fn()

        assert "No accounts configured" in result

    def test_single_account(self) -> None:
        """Test list_accounts with single account."""
        with patch(
            "read_no_evil_mcp.tools.list_accounts.list_configured_accounts",
            return_value=["default"],
        ):
            result = list_accounts.fn()

        assert "default" in result
