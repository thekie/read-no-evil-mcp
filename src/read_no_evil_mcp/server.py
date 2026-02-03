"""MCP server implementation for read-no-evil-mcp."""

from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from read_no_evil_mcp.config import Settings
from read_no_evil_mcp.connectors.imap import IMAPConnector
from read_no_evil_mcp.models import IMAPConfig
from read_no_evil_mcp.service import EmailService
from read_no_evil_mcp.tools import execute_tool, get_all_tools

# Create the MCP server instance
server = Server("read-no-evil-mcp")


def _create_service() -> EmailService:
    """Create an EmailService from environment configuration."""
    settings = Settings()  # type: ignore[call-arg]
    config = IMAPConfig(
        host=settings.imap_host,
        port=settings.imap_port,
        username=settings.imap_username,
        password=settings.imap_password,
        ssl=settings.imap_ssl,
    )
    connector = IMAPConnector(config)
    return EmailService(connector)


@server.list_tools()  # type: ignore[no-untyped-call,untyped-decorator]
async def list_tools() -> list[Tool]:
    """Return the list of available tools."""
    return get_all_tools()


@server.call_tool()  # type: ignore[untyped-decorator]
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    service = _create_service()

    try:
        service.connect()
        return execute_tool(name, arguments, service)
    except KeyError:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
    finally:
        service.disconnect()


async def run_server() -> None:
    """Run the MCP server using stdio transport."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main() -> None:
    """Entry point for the MCP server."""
    import asyncio

    asyncio.run(run_server())


if __name__ == "__main__":
    main()
