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
            attachments=[
                Attachment(filename="file.pdf", content_type="application/pdf", size=100)
            ],
            message_id="<abc123@example.com>",
        )
        assert len(email.to) == 1
        assert len(email.cc) == 1
        assert len(email.attachments) == 1
        assert email.message_id == "<abc123@example.com>"
