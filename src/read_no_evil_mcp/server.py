"""MCP server implementation for read-no-evil-mcp using FastMCP."""

from read_no_evil_mcp.tools import mcp


def main() -> None:
    """Entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
