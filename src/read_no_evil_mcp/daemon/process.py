"""Daemon process management (start/stop/status)."""

from typing import Any

import os
import signal
import sys
import time

import structlog

from read_no_evil_mcp.daemon.client import DaemonClient
from read_no_evil_mcp.daemon.paths import get_pid_path, get_socket_path

logger = structlog.get_logger()

STARTUP_TIMEOUT = 120  # seconds (model loading can take a while)
SHUTDOWN_TIMEOUT = 10  # seconds


def _read_pid() -> int | None:
    """Read PID from pid file, return None if not found or invalid."""
    pid_path = get_pid_path()
    if not pid_path.exists():
        return None

    try:
        pid = int(pid_path.read_text().strip())
        # Check if process exists
        os.kill(pid, 0)
        return pid
    except (ValueError, ProcessLookupError, PermissionError):
        # PID file is stale, remove it
        pid_path.unlink(missing_ok=True)
        return None


def _write_pid(pid: int) -> None:
    """Write PID to pid file."""
    pid_path = get_pid_path()
    pid_path.write_text(str(pid))
    pid_path.chmod(0o600)


def _remove_pid() -> None:
    """Remove PID file."""
    get_pid_path().unlink(missing_ok=True)


def _daemonize() -> None:
    """Double-fork to daemonize the process."""
    # First fork
    pid = os.fork()
    if pid > 0:
        # Parent exits
        sys.exit(0)

    # Create new session
    os.setsid()

    # Second fork
    pid = os.fork()
    if pid > 0:
        # First child exits
        sys.exit(0)

    # Redirect standard file descriptors to /dev/null
    sys.stdout.flush()
    sys.stderr.flush()

    with open("/dev/null", "rb") as devnull:
        os.dup2(devnull.fileno(), sys.stdin.fileno())
    with open("/dev/null", "ab") as devnull:
        os.dup2(devnull.fileno(), sys.stdout.fileno())
        os.dup2(devnull.fileno(), sys.stderr.fileno())


def start_daemon(foreground: bool = False) -> bool:
    """Start the daemon process.

    Args:
        foreground: If True, run in foreground (for debugging).

    Returns:
        True if daemon started successfully.
    """
    # Check if already running
    existing_pid = _read_pid()
    if existing_pid is not None:
        client = DaemonClient()
        if client.ping():
            logger.warning("Daemon already running", pid=existing_pid)
            return False
        else:
            # Stale PID, clean up
            _remove_pid()
            get_socket_path().unlink(missing_ok=True)

    if foreground:
        # Run in foreground
        _write_pid(os.getpid())
        try:
            from read_no_evil_mcp.daemon.server import run_server

            run_server()
        finally:
            _remove_pid()
        return True

    # Daemonize
    _daemonize()

    # We're now in the daemon process
    _write_pid(os.getpid())

    try:
        from read_no_evil_mcp.daemon.server import run_server

        run_server()
    finally:
        _remove_pid()

    return True


def stop_daemon() -> bool:
    """Stop the running daemon.

    Returns:
        True if daemon was stopped, False if not running.
    """
    pid = _read_pid()
    if pid is None:
        logger.info("Daemon is not running")
        return False

    logger.info("Stopping daemon", pid=pid)

    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        # Already dead
        _remove_pid()
        get_socket_path().unlink(missing_ok=True)
        return True

    # Wait for shutdown
    for _ in range(SHUTDOWN_TIMEOUT * 10):
        try:
            os.kill(pid, 0)
            time.sleep(0.1)
        except ProcessLookupError:
            break
    else:
        # Force kill if still running
        logger.warning("Daemon did not stop gracefully, killing", pid=pid)
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    _remove_pid()
    get_socket_path().unlink(missing_ok=True)
    logger.info("Daemon stopped")
    return True


def daemon_status() -> dict[str, Any]:
    """Get daemon status information.

    Returns:
        Dict with status information.
    """
    pid = _read_pid()
    socket_exists = get_socket_path().exists()

    if pid is None:
        return {
            "running": False,
            "pid": None,
            "socket_exists": socket_exists,
            "responsive": False,
        }

    client = DaemonClient()
    responsive = client.ping()

    return {
        "running": True,
        "pid": pid,
        "socket_exists": socket_exists,
        "responsive": responsive,
    }
