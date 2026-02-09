"""CLI entry point for read-no-evil-mcp daemon management."""

import argparse
import sys


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="rnoe",
        description="Read No Evil MCP - Email security with prompt injection protection",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # daemon subcommand
    daemon_parser = subparsers.add_parser(
        "daemon",
        help="Manage the scan daemon",
    )
    daemon_parser.add_argument(
        "action",
        choices=["start", "stop", "status", "run"],
        help="Daemon action (run = foreground mode for debugging)",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    if args.command == "daemon":
        return _handle_daemon(args.action)

    return 0


def _handle_daemon(action: str) -> int:
    """Handle daemon subcommand."""
    from read_no_evil_mcp.daemon import daemon_status, start_daemon, stop_daemon

    if action == "start":
        print("Starting daemon (this may take 30-60s for model loading)...")
        # Fork and return immediately
        import os

        pid = os.fork()
        if pid > 0:
            # Parent: wait a moment and check status
            import time

            time.sleep(2)
            status = daemon_status()
            if status["running"]:
                print(f"✓ Daemon started (PID: {status['pid']})")
                return 0
            else:
                print("✗ Daemon failed to start")
                return 1
        else:
            # Child: start daemon
            start_daemon(foreground=False)
            return 0

    elif action == "stop":
        if stop_daemon():
            print("✓ Daemon stopped")
            return 0
        else:
            print("Daemon was not running")
            return 0

    elif action == "status":
        status = daemon_status()
        if status["running"]:
            responsive = "✓ responsive" if status["responsive"] else "✗ not responding"
            print(f"Daemon is running (PID: {status['pid']}) - {responsive}")
        else:
            print("Daemon is not running")
        return 0

    elif action == "run":
        print("Running daemon in foreground (Ctrl+C to stop)...")
        start_daemon(foreground=True)
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
