"""Daemon mode for read-no-evil-mcp.

Provides a background server that keeps the DeBERTa model loaded,
reducing scan latency from 30-60s to ~100ms.
"""

from read_no_evil_mcp.daemon.client import DaemonClient
from read_no_evil_mcp.daemon.paths import get_pid_path, get_runtime_dir, get_socket_path
from read_no_evil_mcp.daemon.process import daemon_status, start_daemon, stop_daemon
from read_no_evil_mcp.daemon.server import DaemonServer

__all__ = [
    "DaemonClient",
    "DaemonServer",
    "daemon_status",
    "get_pid_path",
    "get_runtime_dir",
    "get_socket_path",
    "start_daemon",
    "stop_daemon",
]
