"""Daemon server for prompt injection scanning.

Runs as a background process, keeping the DeBERTa model loaded
and serving scan requests over a Unix socket.
"""

import asyncio
import json
import signal
from pathlib import Path
from typing import Any

import structlog

from read_no_evil_mcp.daemon.paths import get_socket_path
from read_no_evil_mcp.protection.heuristic import HeuristicScanner

logger = structlog.get_logger()

MAX_REQUEST_SIZE = 1024 * 1024  # 1MB


class DaemonServer:
    """Async Unix socket server for prompt injection scanning."""

    def __init__(self, socket_path: Path | None = None) -> None:
        """Initialize the daemon server.

        Args:
            socket_path: Path to Unix socket. Defaults to standard location.
        """
        self._socket_path = socket_path or get_socket_path()
        self._scanner: HeuristicScanner | None = None
        self._server: asyncio.Server | None = None
        self._running = False

    def _get_scanner(self) -> HeuristicScanner:
        """Get or create the scanner instance."""
        if self._scanner is None:
            logger.info("Loading prompt injection model (this may take a moment)...")
            self._scanner = HeuristicScanner()
            # Force model loading by doing a test scan
            self._scanner.scan("test")
            logger.info("Model loaded successfully")
        return self._scanner

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle a single client connection."""
        try:
            while True:
                # Read line (newline-delimited JSON)
                line = await reader.readline()
                if not line:
                    break

                if len(line) > MAX_REQUEST_SIZE:
                    response = {"error": "Request too large"}
                else:
                    response = await self._handle_request(line.decode().strip())

                writer.write((json.dumps(response) + "\n").encode())
                await writer.drain()
        except Exception as e:
            logger.error("Client handler error", error=str(e))
        finally:
            writer.close()
            await writer.wait_closed()

    async def _handle_request(self, request_str: str) -> dict[str, Any]:
        """Handle a JSON request and return response."""
        try:
            request = json.loads(request_str)
        except json.JSONDecodeError:
            return {"error": "Invalid JSON"}

        method = request.get("method")

        if method == "ping":
            return {"status": "ok"}

        if method == "scan":
            content = request.get("content", "")
            if not isinstance(content, str):
                return {"error": "content must be a string"}

            scanner = self._get_scanner()
            result = scanner.scan(content)
            return {
                "is_safe": result.is_safe,
                "score": result.score,
                "detected_patterns": result.detected_patterns,
            }

        return {"error": f"Unknown method: {method}"}

    async def start(self) -> None:
        """Start the daemon server."""
        # Remove stale socket file
        if self._socket_path.exists():
            self._socket_path.unlink()

        # Pre-load the model
        self._get_scanner()

        # Start server
        self._server = await asyncio.start_unix_server(
            self._handle_client,
            path=str(self._socket_path),
        )
        self._running = True

        # Set socket permissions (owner only)
        self._socket_path.chmod(0o600)

        logger.info("Daemon server started", socket=str(self._socket_path))

        async with self._server:
            await self._server.serve_forever()

    async def stop(self) -> None:
        """Stop the daemon server."""
        self._running = False
        if self._server:
            self._server.close()
            await self._server.wait_closed()

        # Clean up socket file
        if self._socket_path.exists():
            self._socket_path.unlink()

        logger.info("Daemon server stopped")


def run_server(socket_path: Path | None = None) -> None:
    """Run the daemon server (blocking).

    Args:
        socket_path: Optional custom socket path.
    """
    server = DaemonServer(socket_path)

    # Handle shutdown signals
    def signal_handler(sig: int, frame: Any) -> None:
        logger.info("Received shutdown signal", signal=sig)
        asyncio.get_event_loop().call_soon_threadsafe(lambda: asyncio.create_task(server.stop()))

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Run server
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        pass
