"""Tests for email data models."""

import pytest

from read_no_evil_mcp.email.models import OutgoingAttachment


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
