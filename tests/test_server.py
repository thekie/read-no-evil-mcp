"""Tests for MCP server."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from read_no_evil_mcp.models import Email, EmailAddress, EmailSummary, Folder
from read_no_evil_mcp.server import call_tool, list_tools


class TestListTools:
    @pytest.mark.asyncio
    async def test_returns_all_tools(self):
        """Test that all expected tools are registered."""
        tools = await list_tools()

        tool_names = {t.name for t in tools}
        assert tool_names == {"list_folders", "list_emails", "get_email"}

    @pytest.mark.asyncio
    async def test_list_folders_tool_schema(self):
        """Test list_folders tool has correct schema."""
        tools = await list_tools()
        tool = next(t for t in tools if t.name == "list_folders")

        assert tool.description == "List all available email folders/mailboxes"
        assert tool.inputSchema["required"] == []

    @pytest.mark.asyncio
    async def test_list_emails_tool_schema(self):
        """Test list_emails tool has correct schema."""
        tools = await list_tools()
        tool = next(t for t in tools if t.name == "list_emails")

        assert "folder" in tool.inputSchema["properties"]
        assert "days_back" in tool.inputSchema["properties"]
        assert "limit" in tool.inputSchema["properties"]

    @pytest.mark.asyncio
    async def test_get_email_tool_schema(self):
        """Test get_email tool has correct schema."""
        tools = await list_tools()
        tool = next(t for t in tools if t.name == "get_email")

        assert tool.inputSchema["required"] == ["folder", "uid"]
        assert "folder" in tool.inputSchema["properties"]
        assert "uid" in tool.inputSchema["properties"]


class TestCallTool:
    @pytest.mark.asyncio
    async def test_list_folders(self):
        """Test list_folders tool returns folder names."""
        mock_service = MagicMock()
        mock_service.list_folders.return_value = [
            Folder(name="INBOX"),
            Folder(name="Sent"),
        ]

        with patch("read_no_evil_mcp.server._create_service", return_value=mock_service):
            result = await call_tool("list_folders", {})

        assert len(result) == 1
        assert "INBOX" in result[0].text
        assert "Sent" in result[0].text
        mock_service.connect.assert_called_once()
        mock_service.disconnect.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_folders_empty(self):
        """Test list_folders with no folders."""
        mock_service = MagicMock()
        mock_service.list_folders.return_value = []

        with patch("read_no_evil_mcp.server._create_service", return_value=mock_service):
            result = await call_tool("list_folders", {})

        assert "No folders found" in result[0].text

    @pytest.mark.asyncio
    async def test_list_emails(self):
        """Test list_emails tool returns email summaries."""
        mock_service = MagicMock()
        mock_service.fetch_emails.return_value = [
            EmailSummary(
                uid=1,
                folder="INBOX",
                subject="Test Subject",
                sender=EmailAddress(address="sender@example.com"),
                date=datetime(2026, 2, 3, 12, 0, 0),
                has_attachments=True,
            ),
        ]

        with patch("read_no_evil_mcp.server._create_service", return_value=mock_service):
            result = await call_tool("list_emails", {"folder": "INBOX", "days_back": 7})

        assert len(result) == 1
        assert "[1]" in result[0].text
        assert "Test Subject" in result[0].text
        assert "sender@example.com" in result[0].text
        assert "[+]" in result[0].text  # attachment marker

    @pytest.mark.asyncio
    async def test_list_emails_no_results(self):
        """Test list_emails with no emails."""
        mock_service = MagicMock()
        mock_service.fetch_emails.return_value = []

        with patch("read_no_evil_mcp.server._create_service", return_value=mock_service):
            result = await call_tool("list_emails", {})

        assert "No emails found" in result[0].text

    @pytest.mark.asyncio
    async def test_list_emails_with_limit(self):
        """Test list_emails respects limit parameter."""
        mock_service = MagicMock()
        mock_service.fetch_emails.return_value = []

        with patch("read_no_evil_mcp.server._create_service", return_value=mock_service):
            await call_tool("list_emails", {"folder": "INBOX", "limit": 5})

        call_args = mock_service.fetch_emails.call_args
        assert call_args.kwargs["limit"] == 5

    @pytest.mark.asyncio
    async def test_get_email(self):
        """Test get_email tool returns full email content."""
        mock_service = MagicMock()
        mock_service.get_email.return_value = Email(
            uid=123,
            folder="INBOX",
            subject="Test Email",
            sender=EmailAddress(name="Sender", address="sender@example.com"),
            date=datetime(2026, 2, 3, 12, 0, 0),
            to=[EmailAddress(address="to@example.com")],
            body_plain="Hello, World!",
            message_id="<abc@example.com>",
        )

        with patch("read_no_evil_mcp.server._create_service", return_value=mock_service):
            result = await call_tool("get_email", {"folder": "INBOX", "uid": 123})

        text = result[0].text
        assert "Subject: Test Email" in text
        assert "From: Sender <sender@example.com>" in text
        assert "To: to@example.com" in text
        assert "Hello, World!" in text

    @pytest.mark.asyncio
    async def test_get_email_not_found(self):
        """Test get_email with non-existent email."""
        mock_service = MagicMock()
        mock_service.get_email.return_value = None

        with patch("read_no_evil_mcp.server._create_service", return_value=mock_service):
            result = await call_tool("get_email", {"folder": "INBOX", "uid": 999})

        assert "Email not found" in result[0].text

    @pytest.mark.asyncio
    async def test_get_email_html_only(self):
        """Test get_email with HTML-only content."""
        mock_service = MagicMock()
        mock_service.get_email.return_value = Email(
            uid=123,
            folder="INBOX",
            subject="HTML Email",
            sender=EmailAddress(address="sender@example.com"),
            date=datetime(2026, 2, 3, 12, 0, 0),
            body_html="<p>HTML content</p>",
        )

        with patch("read_no_evil_mcp.server._create_service", return_value=mock_service):
            result = await call_tool("get_email", {"folder": "INBOX", "uid": 123})

        text = result[0].text
        assert "HTML content - plain text not available" in text
        assert "<p>HTML content</p>" in text

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        """Test calling unknown tool returns error message."""
        mock_service = MagicMock()

        with patch("read_no_evil_mcp.server._create_service", return_value=mock_service):
            result = await call_tool("unknown_tool", {})

        assert "Unknown tool" in result[0].text

    @pytest.mark.asyncio
    async def test_disconnect_called_on_exception(self):
        """Test that disconnect is called even when exception occurs."""
        mock_service = MagicMock()
        mock_service.list_folders.side_effect = RuntimeError("Connection error")

        with patch("read_no_evil_mcp.server._create_service", return_value=mock_service):
            with pytest.raises(RuntimeError):
                await call_tool("list_folders", {})

        mock_service.disconnect.assert_called_once()
