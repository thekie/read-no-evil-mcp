"""Tests for send_email tool."""

import base64
from pathlib import Path
from unittest.mock import MagicMock, patch

from read_no_evil_mcp.email.models import OutgoingAttachment
from read_no_evil_mcp.exceptions import PermissionDeniedError
from read_no_evil_mcp.tools.send_email import _parse_attachments, send_email


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

        assert result == "Email sent successfully to recipient@example.com"
        mock_mailbox.send_email.assert_called_once_with(
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Test body",
            cc=None,
            reply_to=None,
            attachments=None,
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

        assert result == (
            "Email sent successfully to recipient@example.com"
            " (CC: cc1@example.com, cc2@example.com)"
        )
        mock_mailbox.send_email.assert_called_once_with(
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Test body",
            cc=["cc1@example.com", "cc2@example.com"],
            reply_to=None,
            attachments=None,
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

        assert result == "Email sent successfully to recipient@example.com"
        mock_mailbox.send_email.assert_called_once_with(
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Test body",
            cc=None,
            reply_to="replies@example.com",
            attachments=None,
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

        assert result == "Email sent successfully to r1@example.com, r2@example.com"

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

        assert result == "Permission denied: Send access denied for this account"

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

        assert result == "Error: Sending not configured for this account"

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

    def test_send_email_with_attachment(self) -> None:
        """Test send_email tool with a single attachment."""
        mock_mailbox = MagicMock()
        mock_mailbox.send_email.return_value = True
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        content = b"Hello, attachment!"
        content_b64 = base64.b64encode(content).decode()

        with patch(
            "read_no_evil_mcp.tools.send_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = send_email.fn(
                account="work",
                to=["recipient@example.com"],
                subject="Test with attachment",
                body="See attachment",
                attachments=[
                    {
                        "filename": "test.txt",
                        "content": content_b64,
                        "mime_type": "text/plain",
                    }
                ],
            )

        assert result == (
            "Email sent successfully to recipient@example.com with 1 attachment(s): test.txt"
        )

        # Verify attachment was passed to mailbox
        call_args = mock_mailbox.send_email.call_args
        attachments = call_args.kwargs.get("attachments")
        assert attachments is not None
        assert len(attachments) == 1
        assert attachments[0].filename == "test.txt"
        assert attachments[0].get_content() == content

    def test_send_email_with_multiple_attachments(self) -> None:
        """Test send_email tool with multiple attachments."""
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
                subject="Multiple attachments",
                body="See attachments",
                attachments=[
                    {
                        "filename": "doc.pdf",
                        "content": base64.b64encode(b"pdf content").decode(),
                        "mime_type": "application/pdf",
                    },
                    {
                        "filename": "image.png",
                        "content": base64.b64encode(b"png content").decode(),
                        "mime_type": "image/png",
                    },
                ],
            )

        assert result == (
            "Email sent successfully to recipient@example.com"
            " with 2 attachment(s): doc.pdf, image.png"
        )

    def test_send_email_with_path_attachment(self, tmp_path) -> None:
        """Test send_email tool with file path attachment."""
        mock_mailbox = MagicMock()
        mock_mailbox.send_email.return_value = True
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        # Create temp file
        file_path = tmp_path / "report.csv"
        file_path.write_bytes(b"name,value\ntest,123")

        with patch(
            "read_no_evil_mcp.tools.send_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = send_email.fn(
                account="work",
                to=["recipient@example.com"],
                subject="Report",
                body="See report",
                attachments=[
                    {
                        "filename": "report.csv",
                        "path": str(file_path),
                        "mime_type": "text/csv",
                    }
                ],
            )

        assert result == (
            "Email sent successfully to recipient@example.com with 1 attachment(s): report.csv"
        )

    def test_send_email_attachment_missing_filename(self) -> None:
        """Test send_email returns error when attachment is missing filename."""
        mock_mailbox = MagicMock()
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.send_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = send_email.fn(
                account="work",
                to=["recipient@example.com"],
                subject="Test",
                body="Test body",
                attachments=[{"content": base64.b64encode(b"data").decode()}],
            )

        assert result.startswith("Invalid input:")
        assert "filename" in result

    def test_send_email_attachment_missing_content_and_path(self) -> None:
        """Test send_email returns error when attachment has neither content nor path."""
        mock_mailbox = MagicMock()
        mock_mailbox.__enter__ = MagicMock(return_value=mock_mailbox)
        mock_mailbox.__exit__ = MagicMock(return_value=None)

        with patch(
            "read_no_evil_mcp.tools.send_email.create_securemailbox",
            return_value=mock_mailbox,
        ):
            result = send_email.fn(
                account="work",
                to=["recipient@example.com"],
                subject="Test",
                body="Test body",
                attachments=[{"filename": "test.txt"}],
            )

        assert result == "Invalid input: Attachment 'test.txt' must have either 'content' or 'path'"

    def test_send_email_with_empty_attachments_list(self) -> None:
        """Test send_email with empty attachments list."""
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
                subject="Test",
                body="Test body",
                attachments=[],
            )

        assert result == "Email sent successfully to recipient@example.com"

    def test_send_email_with_none_attachments(self) -> None:
        """Test send_email with None attachments (backwards compat)."""
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
                subject="Test",
                body="Test body",
                attachments=None,
            )

        assert result == "Email sent successfully to recipient@example.com"


class TestParseAttachments:
    """Tests for the _parse_attachments helper function."""

    def test_parse_none_returns_none(self) -> None:
        """Test that None input returns None."""
        assert _parse_attachments(None) is None

    def test_parse_empty_list_returns_none(self) -> None:
        """Test that empty list returns None."""
        assert _parse_attachments([]) is None

    def test_parse_with_content(self) -> None:
        """Test parsing attachment with base64 content."""
        content = b"Hello, World!"
        content_b64 = base64.b64encode(content).decode()

        result = _parse_attachments(
            [
                {
                    "filename": "test.txt",
                    "content": content_b64,
                    "mime_type": "text/plain",
                }
            ]
        )

        assert result is not None
        assert len(result) == 1
        assert isinstance(result[0], OutgoingAttachment)
        assert result[0].filename == "test.txt"
        assert result[0].mime_type == "text/plain"
        assert result[0].get_content() == content

    def test_parse_with_path(self, tmp_path: Path) -> None:
        """Test parsing attachment with file path."""
        # Create a real temp file
        test_file = tmp_path / "file.txt"
        test_file.write_bytes(b"test content")

        result = _parse_attachments(
            [
                {
                    "filename": "test.txt",
                    "path": str(test_file),
                }
            ]
        )

        assert result is not None
        assert len(result) == 1
        assert result[0].filename == "test.txt"
        assert result[0].path == str(test_file)
        assert result[0].mime_type == "application/octet-stream"  # default

    def test_parse_default_mime_type(self) -> None:
        """Test that default MIME type is applied."""
        result = _parse_attachments(
            [
                {
                    "filename": "test.bin",
                    "content": base64.b64encode(b"data").decode(),
                }
            ]
        )

        assert result is not None
        assert result[0].mime_type == "application/octet-stream"

    def test_parse_multiple_attachments(self, tmp_path: Path) -> None:
        """Test parsing multiple attachments."""
        # Create a real temp file for the path-based attachment
        img_file = tmp_path / "img.png"
        img_file.write_bytes(b"png data")

        result = _parse_attachments(
            [
                {
                    "filename": "doc.pdf",
                    "content": base64.b64encode(b"pdf").decode(),
                    "mime_type": "application/pdf",
                },
                {
                    "filename": "img.png",
                    "path": str(img_file),
                    "mime_type": "image/png",
                },
            ]
        )

        assert result is not None
        assert len(result) == 2
        assert result[0].filename == "doc.pdf"
        assert result[1].filename == "img.png"

    def test_parse_with_nonexistent_path_raises_error(self) -> None:
        """Test that non-existent file path raises ValueError early."""
        import pytest

        with pytest.raises(ValueError, match="Attachment file not found"):
            _parse_attachments(
                [
                    {
                        "filename": "missing.txt",
                        "path": "/nonexistent/path/to/file.txt",
                    }
                ]
            )


class TestAttachmentInputValidation:
    """Tests for AttachmentInput field validators."""

    def test_filename_with_slash_rejected(self) -> None:
        import pytest

        from read_no_evil_mcp.tools.models import AttachmentInput

        with pytest.raises(ValueError, match="path separators"):
            AttachmentInput(filename="../etc/passwd", content=base64.b64encode(b"x").decode())

    def test_filename_with_backslash_rejected(self) -> None:
        import pytest

        from read_no_evil_mcp.tools.models import AttachmentInput

        with pytest.raises(ValueError, match="path separators"):
            AttachmentInput(filename="..\\etc\\passwd", content=base64.b64encode(b"x").decode())

    def test_filename_starting_with_dot_rejected(self) -> None:
        import pytest

        from read_no_evil_mcp.tools.models import AttachmentInput

        with pytest.raises(ValueError, match="must not start with"):
            AttachmentInput(filename=".hidden", content=base64.b64encode(b"x").decode())

    def test_empty_filename_rejected(self) -> None:
        import pytest

        from read_no_evil_mcp.tools.models import AttachmentInput

        with pytest.raises(ValueError, match="must not be empty"):
            AttachmentInput(filename="", content=base64.b64encode(b"x").decode())

    def test_invalid_base64_rejected(self) -> None:
        import pytest

        from read_no_evil_mcp.tools.models import AttachmentInput

        with pytest.raises(ValueError, match="valid base64"):
            AttachmentInput(filename="test.txt", content="not-valid-base64!!!")

    def test_valid_base64_accepted(self) -> None:
        from read_no_evil_mcp.tools.models import AttachmentInput

        att = AttachmentInput(filename="test.txt", content=base64.b64encode(b"hello").decode())
        assert att.content is not None

    def test_none_content_accepted(self) -> None:
        from read_no_evil_mcp.tools.models import AttachmentInput

        att = AttachmentInput(filename="test.txt", path="/some/path")
        assert att.content is None
