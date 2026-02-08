"""Tests for data models."""

from datetime import datetime

import pytest

from read_no_evil_mcp.models import (
    Attachment,
    Email,
    EmailAddress,
    EmailSummary,
    Folder,
    IMAPConfig,
    OutgoingAttachment,
    ScanResult,
)


class TestEmailAddress:
    def test_with_name(self):
        addr = EmailAddress(name="John Doe", address="john@example.com")
        assert str(addr) == "John Doe <john@example.com>"

    def test_without_name(self):
        addr = EmailAddress(address="john@example.com")
        assert str(addr) == "john@example.com"

    def test_name_none(self):
        addr = EmailAddress(name=None, address="john@example.com")
        assert str(addr) == "john@example.com"


class TestIMAPConfig:
    def test_defaults(self):
        config = IMAPConfig(
            host="imap.example.com",
            username="user",
            password="secret",
        )
        assert config.port == 993
        assert config.ssl is True

    def test_custom_port(self):
        config = IMAPConfig(
            host="imap.example.com",
            port=143,
            username="user",
            password="secret",
            ssl=False,
        )
        assert config.port == 143
        assert config.ssl is False

    def test_password_is_secret(self):
        config = IMAPConfig(
            host="imap.example.com",
            username="user",
            password="secret",
        )
        assert config.password.get_secret_value() == "secret"
        assert "secret" not in str(config.password)


class TestFolder:
    def test_defaults(self):
        folder = Folder(name="INBOX")
        assert folder.delimiter == "/"
        assert folder.flags == []

    def test_with_flags(self):
        folder = Folder(name="Sent", delimiter=".", flags=["\\Sent", "\\HasNoChildren"])
        assert len(folder.flags) == 2


class TestAttachment:
    def test_basic(self):
        att = Attachment(
            filename="document.pdf",
            content_type="application/pdf",
            size=1024,
        )
        assert att.filename == "document.pdf"
        assert att.size == 1024

    def test_size_optional(self):
        att = Attachment(filename="file.txt", content_type="text/plain")
        assert att.size is None


class TestOutgoingAttachment:
    def test_with_content(self):
        """Test attachment with in-memory content."""
        content = b"Hello, World!"
        att = OutgoingAttachment(
            filename="test.txt",
            content=content,
            mime_type="text/plain",
        )
        assert att.filename == "test.txt"
        assert att.mime_type == "text/plain"
        assert att.get_content() == content

    def test_with_path(self, tmp_path):
        """Test attachment loaded from file path."""
        file_path = tmp_path / "test.txt"
        file_path.write_bytes(b"File content")

        att = OutgoingAttachment(
            filename="test.txt",
            path=str(file_path),
        )
        assert att.get_content() == b"File content"

    def test_default_mime_type(self):
        """Test default MIME type is application/octet-stream."""
        att = OutgoingAttachment(filename="test.bin", content=b"data")
        assert att.mime_type == "application/octet-stream"

    def test_content_takes_precedence_over_path(self, tmp_path):
        """Test that content is used even if path is also provided."""
        file_path = tmp_path / "test.txt"
        file_path.write_bytes(b"File content")

        att = OutgoingAttachment(
            filename="test.txt",
            content=b"Memory content",
            path=str(file_path),
        )
        # Should return in-memory content, not file content
        assert att.get_content() == b"Memory content"

    def test_raises_without_content_or_path(self):
        """Test that get_content raises ValueError if neither is provided."""
        att = OutgoingAttachment(filename="test.txt")
        with pytest.raises(ValueError, match="Either content or path must be provided"):
            att.get_content()

    def test_raises_for_nonexistent_file(self):
        """Test that get_content raises FileNotFoundError for missing file."""
        att = OutgoingAttachment(
            filename="test.txt",
            path="/nonexistent/path/file.txt",
        )
        with pytest.raises(FileNotFoundError):
            att.get_content()

    def test_binary_content(self):
        """Test attachment with binary content."""
        content = bytes(range(256))
        att = OutgoingAttachment(
            filename="binary.bin",
            content=content,
            mime_type="application/octet-stream",
        )
        assert att.get_content() == content


class TestEmailSummary:
    def test_basic(self):
        summary = EmailSummary(
            uid=123,
            folder="INBOX",
            subject="Test Email",
            sender=EmailAddress(address="sender@example.com"),
            date=datetime(2026, 2, 3, 12, 0, 0),
        )
        assert summary.uid == 123
        assert summary.has_attachments is False
        assert summary.is_seen is False

    def test_with_attachments(self):
        summary = EmailSummary(
            uid=123,
            folder="INBOX",
            subject="Test",
            sender=EmailAddress(address="sender@example.com"),
            date=datetime(2026, 2, 3, 12, 0, 0),
            has_attachments=True,
        )
        assert summary.has_attachments is True

    def test_is_seen_default_false(self):
        summary = EmailSummary(
            uid=123,
            folder="INBOX",
            subject="Test",
            sender=EmailAddress(address="sender@example.com"),
            date=datetime(2026, 2, 3, 12, 0, 0),
        )
        assert summary.is_seen is False

    def test_is_seen_explicit_true(self):
        summary = EmailSummary(
            uid=123,
            folder="INBOX",
            subject="Test",
            sender=EmailAddress(address="sender@example.com"),
            date=datetime(2026, 2, 3, 12, 0, 0),
            is_seen=True,
        )
        assert summary.is_seen is True


class TestEmail:
    def test_extends_summary(self):
        email = Email(
            uid=123,
            folder="INBOX",
            subject="Test Email",
            sender=EmailAddress(address="sender@example.com"),
            date=datetime(2026, 2, 3, 12, 0, 0),
            body_plain="Hello, World!",
        )
        assert email.uid == 123
        assert email.body_plain == "Hello, World!"
        assert email.body_html is None
        assert email.attachments == []
        assert email.is_seen is False

    def test_full_email(self):
        email = Email(
            uid=456,
            folder="INBOX",
            subject="Full Email",
            sender=EmailAddress(name="Sender", address="sender@example.com"),
            date=datetime(2026, 2, 3, 12, 0, 0),
            to=[EmailAddress(address="to@example.com")],
            cc=[EmailAddress(address="cc@example.com")],
            body_plain="Plain text",
            body_html="<p>HTML</p>",
            attachments=[Attachment(filename="file.pdf", content_type="application/pdf", size=100)],
            message_id="<abc123@example.com>",
        )
        assert len(email.to) == 1
        assert len(email.cc) == 1
        assert len(email.attachments) == 1
        assert email.message_id == "<abc123@example.com>"

    def test_is_seen_inherited(self):
        email = Email(
            uid=123,
            folder="INBOX",
            subject="Test",
            sender=EmailAddress(address="sender@example.com"),
            date=datetime(2026, 2, 3, 12, 0, 0),
            is_seen=True,
            body_plain="Test body",
        )
        assert email.is_seen is True


class TestScanResult:
    def test_safe_result(self) -> None:
        result = ScanResult(is_safe=True, score=0.0, detected_patterns=[])
        assert result.is_safe
        assert not result.is_blocked
        assert result.score == 0.0
        assert result.detected_patterns == []

    def test_unsafe_result(self) -> None:
        result = ScanResult(
            is_safe=False,
            score=0.8,
            detected_patterns=["ignore_instructions", "you_are_now"],
        )
        assert not result.is_safe
        assert result.is_blocked
        assert result.score == 0.8
        assert len(result.detected_patterns) == 2

    def test_is_blocked_property(self) -> None:
        safe = ScanResult(is_safe=True, score=0.0)
        unsafe = ScanResult(is_safe=False, score=0.5, detected_patterns=["test"])
        assert not safe.is_blocked
        assert unsafe.is_blocked

    def test_default_detected_patterns(self) -> None:
        result = ScanResult(is_safe=True, score=0.0)
        assert result.detected_patterns == []
