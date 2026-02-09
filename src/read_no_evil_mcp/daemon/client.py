"""Daemon client for communicating with the scan daemon."""

from typing import Any

import json
import socket
from pathlib import Path

import structlog

from read_no_evil_mcp.daemon.paths import get_socket_path
from read_no_evil_mcp.models import ScanResult

logger = structlog.get_logger()

DEFAULT_TIMEOUT = 5.0  # seconds


class DaemonClient:
    """Sync client for communicating with the daemon over Unix socket."""

    def __init__(
        self,
        socket_path: Path | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the daemon client.

        Args:
            socket_path: Path to Unix socket. Defaults to standard location.
            timeout: Socket timeout in seconds.
        """
        self._socket_path = socket_path or get_socket_path()
        self._timeout = timeout

    def _send_request(self, request: dict[str, Any]) -> dict[str, Any] | None:
        """Send a request to the daemon and return the response.

        Returns None on any error (connection failed, timeout, etc).
        """
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(self._timeout)
            sock.connect(str(self._socket_path))

            # Send request
            request_bytes = (json.dumps(request) + "\n").encode()
            sock.sendall(request_bytes)

            # Read response (line-delimited)
            response_bytes = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response_bytes += chunk
                if b"\n" in response_bytes:
                    break

            sock.close()

            if not response_bytes:
                return None

            result: dict[str, Any] = json.loads(response_bytes.decode().strip())
            return result
        except Exception as e:
            logger.debug("Daemon request failed", error=str(e))
            return None

    def is_available(self) -> bool:
        """Check if the daemon is available and responding."""
        return self.ping()

    def ping(self) -> bool:
        """Ping the daemon to check if it's alive.

        Returns True if daemon responded, False otherwise.
        """
        response = self._send_request({"method": "ping"})
        return response is not None and response.get("status") == "ok"

    def scan(self, content: str) -> ScanResult | None:
        """Scan content for prompt injection via the daemon.

        Args:
            content: Text content to scan.

        Returns:
            ScanResult if successful, None if daemon unavailable.
        """
        response = self._send_request({"method": "scan", "content": content})

        if response is None or "error" in response:
            return None

        return ScanResult(
            is_safe=response.get("is_safe", True),
            score=response.get("score", 0.0),
            detected_patterns=response.get("detected_patterns", []),
        )
