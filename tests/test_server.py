"""Tests for MCP server protocol flow."""

from collections.abc import AsyncIterator
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from fastmcp import Client
from fastmcp.exceptions import ToolError

from read_no_evil_mcp.exceptions import (
    AccountNotFoundError,
    ConfigError,
    PermissionDeniedError,
)
from read_no_evil_mcp.tools import mcp

EXPECTED_TOOLS = {
    "delete_email",
    "get_email",
    "list_accounts",
    "list_emails",
    "list_folders",
    "move_email",
    "send_email",
}


@pytest_asyncio.fixture
async def client() -> AsyncIterator[Client]:
    async with Client(mcp) as c:
        yield c


def _mock_mailbox(**method_returns: object) -> MagicMock:
    mb = MagicMock()
    mb.__enter__ = MagicMock(return_value=mb)
    mb.__exit__ = MagicMock(return_value=None)
    for method, retval in method_returns.items():
        getattr(mb, method).return_value = retval
    return mb


@pytest.mark.asyncio
class TestToolDiscovery:
    async def test_lists_all_tools(self, client: Client) -> None:
        tools = await client.list_tools()
        assert {t.name for t in tools} == EXPECTED_TOOLS

    async def test_each_tool_has_description(self, client: Client) -> None:
        tools = await client.list_tools()
        for tool in tools:
            assert tool.description, f"{tool.name} has no description"


@pytest.mark.asyncio
class TestListAccounts:
    async def test_returns_accounts(self, client: Client) -> None:
        with patch(
            "read_no_evil_mcp.tools.list_accounts.list_configured_accounts",
            return_value=["work", "personal"],
        ):
            result = await client.call_tool("list_accounts", {})
        assert "work" in result.data
        assert "personal" in result.data

    async def test_no_accounts_raises(self, client: Client) -> None:
        with (
            patch(
                "read_no_evil_mcp.tools.list_accounts.list_configured_accounts",
                side_effect=ConfigError("No accounts configured."),
            ),
            pytest.raises(ToolError, match="No accounts configured"),
        ):
            await client.call_tool("list_accounts", {})


@pytest.mark.asyncio
class TestListFolders:
    async def test_returns_folders(self, client: Client) -> None:
        from read_no_evil_mcp.email.models import Folder

        mb = _mock_mailbox(list_folders=[Folder(name="INBOX"), Folder(name="Sent")])
        with patch(
            "read_no_evil_mcp.tools.list_folders.create_securemailbox",
            return_value=mb,
        ):
            result = await client.call_tool("list_folders", {"account": "work"})
        assert "INBOX" in result.data
        assert "Sent" in result.data

    async def test_account_not_found(self, client: Client) -> None:
        with patch(
            "read_no_evil_mcp.tools.list_folders.create_securemailbox",
            side_effect=AccountNotFoundError("bad-acct"),
        ):
            result = await client.call_tool("list_folders", {"account": "bad-acct"})
        assert "Account not found" in result.data


@pytest.mark.asyncio
class TestListEmails:
    async def test_empty_folder(self, client: Client) -> None:
        mb = _mock_mailbox(fetch_emails=[])
        with patch(
            "read_no_evil_mcp.tools.list_emails.create_securemailbox",
            return_value=mb,
        ):
            result = await client.call_tool("list_emails", {"account": "work", "folder": "INBOX"})
        assert result.data is not None

    async def test_permission_denied(self, client: Client) -> None:
        mb = _mock_mailbox()
        mb.fetch_emails.side_effect = PermissionDeniedError("Read access denied")
        with patch(
            "read_no_evil_mcp.tools.list_emails.create_securemailbox",
            return_value=mb,
        ):
            result = await client.call_tool("list_emails", {"account": "work", "folder": "INBOX"})
        assert "Permission denied" in result.data


@pytest.mark.asyncio
class TestGetEmail:
    async def test_account_not_found(self, client: Client) -> None:
        with patch(
            "read_no_evil_mcp.tools.get_email.create_securemailbox",
            side_effect=AccountNotFoundError("missing"),
        ):
            result = await client.call_tool(
                "get_email", {"account": "missing", "folder": "INBOX", "uid": 1}
            )
        assert "Account not found" in result.data


@pytest.mark.asyncio
class TestSendEmail:
    async def test_permission_denied(self, client: Client) -> None:
        mb = _mock_mailbox()
        mb.send_email.side_effect = PermissionDeniedError("Send not allowed")
        with patch(
            "read_no_evil_mcp.tools.send_email.create_securemailbox",
            return_value=mb,
        ):
            result = await client.call_tool(
                "send_email",
                {
                    "account": "work",
                    "to": ["user@example.com"],
                    "subject": "Hi",
                    "body": "Hello",
                },
            )
        assert "Permission denied" in result.data


@pytest.mark.asyncio
class TestMoveEmail:
    async def test_account_not_found(self, client: Client) -> None:
        with patch(
            "read_no_evil_mcp.tools.move_email.create_securemailbox",
            side_effect=AccountNotFoundError("gone"),
        ):
            result = await client.call_tool(
                "move_email",
                {
                    "account": "gone",
                    "folder": "INBOX",
                    "uid": 1,
                    "target_folder": "Archive",
                },
            )
        assert "Account not found" in result.data


@pytest.mark.asyncio
class TestDeleteEmail:
    async def test_account_not_found(self, client: Client) -> None:
        with patch(
            "read_no_evil_mcp.tools.delete_email.create_securemailbox",
            side_effect=AccountNotFoundError("gone"),
        ):
            result = await client.call_tool(
                "delete_email", {"account": "gone", "folder": "INBOX", "uid": 1}
            )
        assert "Account not found" in result.data


@pytest.mark.asyncio
class TestInvalidInvocations:
    async def test_unknown_tool(self, client: Client) -> None:
        with pytest.raises(ToolError, match="Unknown tool"):
            await client.call_tool("nonexistent_tool", {})

    async def test_missing_required_param(self, client: Client) -> None:
        with pytest.raises(ToolError, match="Missing required argument"):
            await client.call_tool("list_folders", {})
