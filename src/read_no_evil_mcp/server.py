"""MCP server implementation for read-no-evil-mcp using FastMCP."""

import os
import sys

from read_no_evil_mcp.config import load_settings
from read_no_evil_mcp.exceptions import ConfigError
from read_no_evil_mcp.tools import mcp


def main() -> None:
    """Entry point for the MCP server."""
    # Validate configuration at startup (fail fast with friendly messages)
    try:
        load_settings()
    except ConfigError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    transport = os.environ.get("RNOE_TRANSPORT", "stdio")

    if transport == "http":
        host = os.environ.get("RNOE_HTTP_HOST", "0.0.0.0")
        port = int(os.environ.get("RNOE_HTTP_PORT", "8000"))
        mcp.run(transport="http", host=host, port=port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
