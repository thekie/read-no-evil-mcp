"""MCP server implementation for read-no-evil-mcp."""

from datetime import timedelta
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from read_no_evil_mcp.config import Settings
from read_no_evil_mcp.connectors.imap import IMAPConnector
from read_no_evil_mcp.models import Email, IMAPConfig
from read_no_evil_mcp.service import EmailService

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
    return [
        Tool(
            name="list_folders",
            description="List all available email folders/mailboxes",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="list_emails",
            description="List email summaries from a folder",
            inputSchema={
                "type": "object",
                "properties": {
                    "folder": {
                        "type": "string",
                        "description": "Folder to list emails from (default: INBOX)",
                        "default": "INBOX",
                    },
                    "days_back": {
                        "type": "integer",
                        "description": "Number of days to look back (default: 7)",
                        "default": 7,
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of emails to return",
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="get_email",
            description="Get full email content by UID",
            inputSchema={
                "type": "object",
                "properties": {
                    "folder": {
                        "type": "string",
                        "description": "Folder containing the email",
                    },
                    "uid": {
                        "type": "integer",
                        "description": "Unique identifier of the email",
                    },
                },
                "required": ["folder", "uid"],
            },
        ),
    ]


@server.call_tool()  # type: ignore[untyped-decorator]
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    service = _create_service()

    try:
        service.connect()

        if name == "list_folders":
            folders = service.list_folders()
            result = "\n".join(f"- {f.name}" for f in folders)
            return [TextContent(type="text", text=result or "No folders found.")]

        elif name == "list_emails":
            folder = arguments.get("folder", "INBOX")
            days_back = arguments.get("days_back", 7)
            limit = arguments.get("limit")

            emails = service.fetch_emails(
                folder,
                lookback=timedelta(days=days_back),
                limit=limit,
            )

            if not emails:
                return [TextContent(type="text", text="No emails found.")]

            lines = []
            for email in emails:
                date_str = email.date.strftime("%Y-%m-%d %H:%M")
                attachment_marker = " [+]" if email.has_attachments else ""
                lines.append(
                    f"[{email.uid}] {date_str} | {email.sender.address} | "
                    f"{email.subject}{attachment_marker}"
                )

            return [TextContent(type="text", text="\n".join(lines))]

        elif name == "get_email":
            folder = arguments["folder"]
            uid = arguments["uid"]

            email_result: Email | None = service.get_email(folder, uid)

            if not email_result:
                return [TextContent(type="text", text=f"Email not found: {folder}/{uid}")]

            # Format email content
            lines = [
                f"Subject: {email_result.subject}",
                f"From: {email_result.sender}",
                f"To: {', '.join(str(addr) for addr in email_result.to)}",
                f"Date: {email_result.date.strftime('%Y-%m-%d %H:%M:%S')}",
            ]

            if email_result.cc:
                lines.append(f"CC: {', '.join(str(addr) for addr in email_result.cc)}")

            if email_result.message_id:
                lines.append(f"Message-ID: {email_result.message_id}")

            if email_result.attachments:
                att_list = ", ".join(a.filename for a in email_result.attachments)
                lines.append(f"Attachments: {att_list}")

            lines.append("")  # Empty line before body

            if email_result.body_plain:
                lines.append(email_result.body_plain)
            elif email_result.body_html:
                lines.append("[HTML content - plain text not available]")
                lines.append(email_result.body_html)
            else:
                lines.append("[No body content]")

            return [TextContent(type="text", text="\n".join(lines))]

        else:
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
