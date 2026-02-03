"""Tests for MCP server setup."""

from read_no_evil_mcp.tools import mcp


class TestMCPSetup:
    def test_mcp_server_name(self) -> None:
        """Test that the MCP server has the correct name."""
        assert mcp.name == "read-no-evil-mcp"

    def test_tools_registered(self) -> None:
        """Test that all expected tools are registered."""
        tool_names = set(mcp._tool_manager._tools.keys())
        assert tool_names == {"list_folders", "list_emails", "get_email"}
