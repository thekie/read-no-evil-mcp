"""Decorator that appends a one-time version update notice to tool responses."""

import logging
from collections.abc import Callable
from functools import wraps
from typing import Any

from read_no_evil_mcp.version_check import get_update_notice

logger = logging.getLogger(__name__)

_notice_shown: bool = False


def append_update_notice(func: Callable[..., str]) -> Callable[..., str]:
    """Wrap an MCP tool to append an update notice on the first call."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        global _notice_shown  # noqa: PLW0603

        result = func(*args, **kwargs)

        if _notice_shown:
            return result

        _notice_shown = True

        notice = get_update_notice()
        if notice:
            return f"{result}\n\n---\n{notice}"

        return result

    return wrapper


def _reset() -> None:
    """Reset module state. For testing only."""
    global _notice_shown  # noqa: PLW0603
    _notice_shown = False
