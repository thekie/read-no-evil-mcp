"""Tests for email data models."""

from datetime import datetime

import pytest

from read_no_evil_mcp.email.models import (
    Attachment,
    Email,
    EmailAddress,
    EmailSummary,
    OutgoingAttachment,
)


class TestEmailSummaryGetScannableContent:
    def test_returns_subject_and_sender_address(self) -> None:
        summary = EmailSummary(
            uid="1",
            folder="INBOX",
            subject="Hello world",
            sender=EmailAddress(address="alice@example.com"),
            date=datetime(2026, 2, 3, 12, 0, 0),
        )

        result = summary.get_scannable_content()

        assert result == {
            "subject": "Hello world",
            "sender_address": "alice@example.com",
        }

    def test_includes_sender_name_when_present(self) -> None:
        summary = EmailSummary(
            uid="1",
            folder="INBOX",
            subject="Hello",
            sender=EmailAddress(name="Alice Smith", address="alice@example.com"),
            date=datetime(2026, 2, 3, 12, 0, 0),
        )

        result = summary.get_scannable_content()

        assert result == {
            "subject": "Hello",
            "sender_name": "Alice Smith",
            "sender_address": "alice@example.com",
        }

    def test_excludes_sender_name_when_none(self) -> None:
        summary = EmailSummary(
            uid="1",
            folder="INBOX",
            subject="Test",
            sender=EmailAddress(name=None, address="bob@example.com"),
            date=datetime(2026, 2, 3, 12, 0, 0),
        )

        result = summary.get_scannable_content()

        assert "sender_name" not in result


class TestEmailGetScannableContent:
    def test_includes_summary_fields_and_body_plain(self) -> None:
        email = Email(
            uid="1",
            folder="INBOX",
            subject="Meeting",
            sender=EmailAddress(name="Boss", address="boss@example.com"),
            date=datetime(2026, 2, 3, 12, 0, 0),
            body_plain="See you at 3pm.",
        )

        result = email.get_scannable_content()

        assert result == {
            "subject": "Meeting",
            "sender_name": "Boss",
            "sender_address": "boss@example.com",
            "body_plain": "See you at 3pm.",
        }

    def test_includes_body_html_when_present(self) -> None:
        email = Email(
            uid="1",
            folder="INBOX",
            subject="Newsletter",
            sender=EmailAddress(address="news@example.com"),
            date=datetime(2026, 2, 3, 12, 0, 0),
            body_html="<p>Hello</p>",
        )

        result = email.get_scannable_content()

        assert result == {
            "subject": "Newsletter",
            "sender_address": "news@example.com",
            "body_html": "<p>Hello</p>",
        }

    def test_includes_attachment_filenames(self) -> None:
        email = Email(
            uid="1",
            folder="INBOX",
            subject="Files",
            sender=EmailAddress(address="sender@example.com"),
            date=datetime(2026, 2, 3, 12, 0, 0),
            attachments=[
                Attachment(filename="report.pdf", content_type="application/pdf"),
                Attachment(filename="data.csv", content_type="text/csv"),
            ],
        )

        result = email.get_scannable_content()

        assert result == {
            "subject": "Files",
            "sender_address": "sender@example.com",
            "attachment_filename_0": "report.pdf",
            "attachment_filename_1": "data.csv",
        }

    def test_no_body_keys_when_body_is_none(self) -> None:
        email = Email(
            uid="1",
            folder="INBOX",
            subject="Empty",
            sender=EmailAddress(address="sender@example.com"),
            date=datetime(2026, 2, 3, 12, 0, 0),
            body_plain=None,
            body_html=None,
        )

        result = email.get_scannable_content()

        assert "body_plain" not in result
        assert "body_html" not in result

    def test_no_attachment_keys_when_no_attachments(self) -> None:
        email = Email(
            uid="1",
            folder="INBOX",
            subject="Plain",
            sender=EmailAddress(address="sender@example.com"),
            date=datetime(2026, 2, 3, 12, 0, 0),
            body_plain="Just text.",
            attachments=[],
        )

        result = email.get_scannable_content()

        assert not any(k.startswith("attachment_filename_") for k in result)


class TestOutgoingAttachmentCheckSize:
    def test_check_size_rejects_oversized(self) -> None:
        attachment = OutgoingAttachment(
            filename="big.bin",
            content=b"x" * 1001,
            mime_type="application/octet-stream",
        )
        with pytest.raises(ValueError, match="Attachment too large"):
            attachment.check_size(max_size=1000)

    def test_check_size_accepts_within_limit(self) -> None:
        attachment = OutgoingAttachment(
            filename="small.bin",
            content=b"x" * 500,
            mime_type="application/octet-stream",
        )
        attachment.check_size(max_size=1000)
