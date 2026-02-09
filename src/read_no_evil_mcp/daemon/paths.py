"""Runtime path helpers for daemon mode."""

import os
from pathlib import Path

import platformdirs


def get_runtime_dir() -> Path:
    """Get the runtime directory for daemon files.

    Uses XDG_RUNTIME_DIR on Linux, falls back to platformdirs.
    """
    # Try XDG_RUNTIME_DIR first (usually /run/user/<uid>)
    xdg_runtime = os.environ.get("XDG_RUNTIME_DIR")
    if xdg_runtime:
        runtime_dir = Path(xdg_runtime) / "read-no-evil-mcp"
    else:
        # Fallback to platformdirs
        runtime_dir = Path(platformdirs.user_runtime_dir("read-no-evil-mcp"))

    # Ensure directory exists
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return runtime_dir


def get_socket_path() -> Path:
    """Get the Unix socket path for daemon communication."""
    return get_runtime_dir() / "scan.sock"


def get_pid_path() -> Path:
    """Get the PID file path for daemon process tracking."""
    return get_runtime_dir() / "daemon.pid"
