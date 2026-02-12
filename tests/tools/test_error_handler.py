"""Tests for the tool error handler decorator."""

import smtplib
from unittest.mock import patch

from imap_tools import ImapToolsError

from read_no_evil_mcp.exceptions import (
    AccountNotFoundError,
    ConfigError,
    CredentialNotFoundError,
    PermissionDeniedError,
)
from read_no_evil_mcp.tools._error_handler import handle_tool_errors


@handle_tool_errors
def _dummy_tool(exc: Exception) -> str:
    raise exc


class TestHandleToolErrors:
    def test_permission_denied(self) -> None:
        result = _dummy_tool(PermissionDeniedError("Read access denied"))
        assert "Permission denied" in result
        assert "Read access denied" in result

    def test_account_not_found(self) -> None:
        result = _dummy_tool(AccountNotFoundError("nonexistent"))
        assert "Account not found" in result
        assert "nonexistent" in result

    def test_credential_not_found(self) -> None:
        result = _dummy_tool(CredentialNotFoundError("work", "WORK_PASSWORD"))
        assert "Configuration error" in result
        assert "WORK_PASSWORD" in result

    def test_config_error(self) -> None:
        result = _dummy_tool(ConfigError("No accounts configured"))
        assert "Configuration error" in result
        assert "No accounts configured" in result

    def test_imap_error(self) -> None:
        result = _dummy_tool(ImapToolsError("LOGIN failed"))
        assert "Email server error" in result

    def test_smtp_auth_error(self) -> None:
        result = _dummy_tool(smtplib.SMTPAuthenticationError(535, b"Authentication failed"))
        assert "authentication failed" in result.lower()

    def test_smtp_error(self) -> None:
        result = _dummy_tool(smtplib.SMTPException("Relay denied"))
        assert "Error sending email" in result
        assert "Relay denied" in result

    def test_value_error(self) -> None:
        result = _dummy_tool(ValueError("Attachment 'f.txt' must have 'content'"))
        assert "Invalid input" in result

    def test_runtime_error(self) -> None:
        result = _dummy_tool(RuntimeError("Not connected"))
        assert "Error" in result
        assert "Not connected" in result

    def test_timeout_error(self) -> None:
        result = _dummy_tool(TimeoutError())
        assert "timed out" in result.lower()

    def test_connection_refused(self) -> None:
        result = _dummy_tool(ConnectionRefusedError("Connection refused"))
        assert "Could not connect" in result

    def test_connection_reset(self) -> None:
        result = _dummy_tool(ConnectionResetError("Connection reset"))
        assert "Could not connect" in result

    def test_os_error(self) -> None:
        result = _dummy_tool(OSError("Name resolution failed"))
        assert "Network error" in result

    def test_unexpected_exception_logged(self) -> None:
        with patch("read_no_evil_mcp.tools._error_handler.logger") as mock_logger:
            result = _dummy_tool(KeyError("something"))

        assert "unexpected error" in result.lower()
        mock_logger.exception.assert_called_once()

    def test_successful_call_passes_through(self) -> None:
        @handle_tool_errors
        def good_tool() -> str:
            return "all good"

        assert good_tool() == "all good"

    def test_preserves_function_name(self) -> None:
        @handle_tool_errors
        def my_tool() -> str:
            return ""

        assert my_tool.__name__ == "my_tool"
