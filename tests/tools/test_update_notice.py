"""Tests for _update_notice decorator."""

import json
from unittest.mock import MagicMock, patch

import pytest

from read_no_evil_mcp import version_check
from read_no_evil_mcp.tools._update_notice import _reset as notice_reset
from read_no_evil_mcp.tools._update_notice import append_update_notice


@pytest.fixture(autouse=True)
def reset_state() -> None:
    """Reset both decorator and version_check module state before each test."""
    notice_reset()
    version_check._reset()


def _make_urlopen_mock(version: str) -> MagicMock:
    payload = {"info": {"version": version}}
    body = json.dumps(payload).encode()
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=MagicMock(read=MagicMock(return_value=body)))
    cm.__exit__ = MagicMock(return_value=False)
    return cm


class TestAppendUpdateNoticeDecorator:
    def test_shows_notice_on_first_call(self) -> None:
        """Decorator appends update notice on first invocation."""

        @append_update_notice
        def my_tool() -> str:
            return "tool output"

        with (
            patch("urllib.request.urlopen", return_value=_make_urlopen_mock("0.9.0")),
            patch("read_no_evil_mcp.version_check.__version__", "0.3.0"),
        ):
            result = my_tool()

        assert result == (
            "tool output\n\n---\n"
            "\u26a0\ufe0f UPDATE AVAILABLE: read-no-evil-mcp v0.9.0 is available "
            "(you are running v0.3.0).\n"
            "Please ask your user to update to get the latest security protections."
        )

    def test_does_not_show_notice_on_second_call(self) -> None:
        """Decorator does not append notice after first invocation."""

        @append_update_notice
        def my_tool() -> str:
            return "tool output"

        with (
            patch("urllib.request.urlopen", return_value=_make_urlopen_mock("0.9.0")),
            patch("read_no_evil_mcp.version_check.__version__", "0.3.0"),
        ):
            my_tool()
            result = my_tool()

        assert result == "tool output"

    def test_passes_through_when_no_update_available(self) -> None:
        """Decorator returns unmodified result when version is current."""

        @append_update_notice
        def my_tool() -> str:
            return "tool output"

        with (
            patch("urllib.request.urlopen", return_value=_make_urlopen_mock("0.3.0")),
            patch("read_no_evil_mcp.version_check.__version__", "0.3.0"),
        ):
            result = my_tool()

        assert result == "tool output"

    def test_passes_through_when_check_fails(self) -> None:
        """Decorator returns unmodified result when PyPI check fails."""
        from urllib.error import URLError

        @append_update_notice
        def my_tool() -> str:
            return "tool output"

        with patch("urllib.request.urlopen", side_effect=URLError("network error")):
            result = my_tool()

        assert result == "tool output"
