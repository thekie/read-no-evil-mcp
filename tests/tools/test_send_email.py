"""Tests for send_email tool."""

from unittest.mock import MagicMock, patch

from read_no_evil_mcp.exceptions import PermissionDeniedError
from read_no_evil_mcp.tools.send_email import send_email


class TestSendEmail:
    def test_send_email_success(self) -> None:
        """Test send_email tool successfully sends email."""
        mock_mailbox = MagicMock()
        mock_mailbox.send_email.return_value = True
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.send_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = send_email.fn(
                account="work",
                to=["recipient@example.com"],
                subject="Test Subject",
                body="Test body",
            )

        assert "Email sent successfully" in result
        assert "recipient@example.com" in result
        mock_mailbox.send_email.assert_called_once_with(
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Test body",
            cc=None,
            reply_to=None,
        )

    def test_send_email_with_cc(self) -> None:
        """Test send_email tool with CC recipients."""
        mock_mailbox = MagicMock()
        mock_mailbox.send_email.return_value = True
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.send_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = send_email.fn(
                account="work",
                to=["recipient@example.com"],
                subject="Test Subject",
                body="Test body",
                cc=["cc1@example.com", "cc2@example.com"],
            )

        assert "Email sent successfully" in result
        assert "recipient@example.com" in result
        assert "CC: cc1@example.com, cc2@example.com" in result
        mock_mailbox.send_email.assert_called_once_with(
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Test body",
            cc=["cc1@example.com", "cc2@example.com"],
            reply_to=None,
        )

    def test_send_email_with_reply_to(self) -> None:
        """Test send_email tool with reply_to parameter."""
        mock_mailbox = MagicMock()
        mock_mailbox.send_email.return_value = True
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.send_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = send_email.fn(
                account="work",
                to=["recipient@example.com"],
                subject="Test Subject",
                body="Test body",
                reply_to="replies@example.com",
            )

        assert "Email sent successfully" in result
        mock_mailbox.send_email.assert_called_once_with(
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Test body",
            cc=None,
            reply_to="replies@example.com",
        )

    def test_send_email_multiple_recipients(self) -> None:
        """Test send_email tool with multiple recipients."""
        mock_mailbox = MagicMock()
        mock_mailbox.send_email.return_value = True
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.send_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = send_email.fn(
                account="work",
                to=["r1@example.com", "r2@example.com"],
                subject="Test",
                body="Test body",
            )

        assert "Email sent successfully" in result
        assert "r1@example.com" in result
        assert "r2@example.com" in result

    def test_send_email_permission_denied(self) -> None:
        """Test send_email returns error when send permission is denied."""
        mock_mailbox = MagicMock()
        mock_mailbox.send_email.side_effect = PermissionDeniedError(
            "Send access denied for this account"
        )
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.send_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = send_email.fn(
                account="restricted",
                to=["recipient@example.com"],
                subject="Test",
                body="Test body",
            )

        assert "Permission denied" in result
        assert "Send access denied" in result

    def test_send_email_sending_not_configured(self) -> None:
        """Test send_email returns error when sending is not configured."""
        mock_mailbox = MagicMock()
        mock_mailbox.send_email.side_effect = RuntimeError(
            "Sending not configured for this account"
        )
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.send_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = send_email.fn(
                account="no-smtp",
                to=["recipient@example.com"],
                subject="Test",
                body="Test body",
            )

        assert "Error" in result
        assert "Sending not configured" in result

    def test_send_email_passes_account_to_create_securemailbox(self) -> None:
        """Test send_email passes account to create_securemailbox."""
        mock_mailbox = MagicMock()
        mock_mailbox.send_email.return_value = True
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.send_email.create_securemailbox",
            return_value=mock_mailbox,
        ) as mock_create:
            send_email.fn(
                account="personal",
                to=["recipient@example.com"],
                subject="Test",
                body="Test body",
            )

        mock_create.assert_called_once_with("personal")
