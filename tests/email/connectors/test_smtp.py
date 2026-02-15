"""Tests for SMTPConnector."""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from read_no_evil_mcp.email.connectors.smtp import SMTPConnector
from read_no_evil_mcp.email.models import OutgoingAttachment
from read_no_evil_mcp.models import SMTPConfig


class TestSMTPConnector:
    @pytest.fixture
    def smtp_config(self) -> SMTPConfig:
        return SMTPConfig(
            host="smtp.example.com",
            port=587,
            username="user@example.com",
            password=SecretStr("password123"),
            ssl=False,
        )

    @pytest.fixture
    def smtp_config_ssl(self) -> SMTPConfig:
        return SMTPConfig(
            host="smtp.example.com",
            port=465,
            username="user@example.com",
            password=SecretStr("password123"),
            ssl=True,
        )

    def test_connect_with_starttls(self, smtp_config: SMTPConfig) -> None:
        """Test SMTP connection using STARTTLS."""
        with patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP") as mock_smtp:
            mock_connection = MagicMock()
            mock_smtp.return_value = mock_connection

            connector = SMTPConnector(smtp_config)
            connector.connect()

            mock_smtp.assert_called_once_with("smtp.example.com", 587)
            mock_connection.starttls.assert_called_once()
            mock_connection.login.assert_called_once_with("user@example.com", "password123")

    def test_connect_with_ssl(self, smtp_config_ssl: SMTPConfig) -> None:
        """Test SMTP connection using SSL."""
        with patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP_SSL") as mock_smtp:
            mock_connection = MagicMock()
            mock_smtp.return_value = mock_connection

            connector = SMTPConnector(smtp_config_ssl)
            connector.connect()

            mock_smtp.assert_called_once_with("smtp.example.com", 465)
            mock_connection.starttls.assert_not_called()
            mock_connection.login.assert_called_once_with("user@example.com", "password123")

    def test_disconnect(self, smtp_config: SMTPConfig) -> None:
        """Test SMTP disconnection."""
        with patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP") as mock_smtp:
            mock_connection = MagicMock()
            mock_smtp.return_value = mock_connection

            connector = SMTPConnector(smtp_config)
            connector.connect()
            connector.disconnect()

            mock_connection.quit.assert_called_once()

    def test_disconnect_when_not_connected(self, smtp_config: SMTPConfig) -> None:
        """Test disconnect when not connected does nothing."""
        connector = SMTPConnector(smtp_config)
        # Should not raise
        connector.disconnect()

    def test_context_manager(self, smtp_config: SMTPConfig) -> None:
        """Test SMTP connector as context manager."""
        with patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP") as mock_smtp:
            mock_connection = MagicMock()
            mock_smtp.return_value = mock_connection

            with SMTPConnector(smtp_config) as connector:
                assert connector is not None

            mock_connection.quit.assert_called_once()

    def test_send_email_basic(self, smtp_config: SMTPConfig) -> None:
        """Test sending a basic email."""
        with patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP") as mock_smtp:
            mock_connection = MagicMock()
            mock_smtp.return_value = mock_connection

            connector = SMTPConnector(smtp_config)
            connector.connect()

            result = connector.send_email(
                from_address="sender@example.com",
                to=["recipient@example.com"],
                subject="Test Subject",
                body="Test body content",
            )

            assert result is True
            mock_connection.sendmail.assert_called_once()
            call_args = mock_connection.sendmail.call_args
            assert call_args[0][0] == "sender@example.com"
            assert call_args[0][1] == ["recipient@example.com"]
            # Check message content
            msg_str = call_args[0][2]
            assert "Test Subject" in msg_str
            assert "Test body content" in msg_str

    def test_send_email_with_cc(self, smtp_config: SMTPConfig) -> None:
        """Test sending email with CC recipients."""
        with patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP") as mock_smtp:
            mock_connection = MagicMock()
            mock_smtp.return_value = mock_connection

            connector = SMTPConnector(smtp_config)
            connector.connect()

            result = connector.send_email(
                from_address="sender@example.com",
                to=["recipient@example.com"],
                subject="Test Subject",
                body="Test body",
                cc=["cc1@example.com", "cc2@example.com"],
            )

            assert result is True
            call_args = mock_connection.sendmail.call_args
            # Recipients should include both to and cc
            recipients = call_args[0][1]
            assert "recipient@example.com" in recipients
            assert "cc1@example.com" in recipients
            assert "cc2@example.com" in recipients
            # Check CC header in message
            msg_str = call_args[0][2]
            assert "Cc: cc1@example.com, cc2@example.com" in msg_str

    def test_send_email_multiple_recipients(self, smtp_config: SMTPConfig) -> None:
        """Test sending email to multiple recipients."""
        with patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP") as mock_smtp:
            mock_connection = MagicMock()
            mock_smtp.return_value = mock_connection

            connector = SMTPConnector(smtp_config)
            connector.connect()

            result = connector.send_email(
                from_address="sender@example.com",
                to=["r1@example.com", "r2@example.com", "r3@example.com"],
                subject="Test",
                body="Test body",
            )

            assert result is True
            call_args = mock_connection.sendmail.call_args
            recipients = call_args[0][1]
            assert recipients == ["r1@example.com", "r2@example.com", "r3@example.com"]

    def test_send_email_not_connected(self, smtp_config: SMTPConfig) -> None:
        """Test send_email raises RuntimeError when not connected."""
        connector = SMTPConnector(smtp_config)

        with pytest.raises(RuntimeError) as exc_info:
            connector.send_email(
                from_address="sender@example.com",
                to=["recipient@example.com"],
                subject="Test",
                body="Test",
            )

        assert "Not connected" in str(exc_info.value)

    def test_send_email_with_reply_to(self, smtp_config: SMTPConfig) -> None:
        """Test sending email with Reply-To header."""
        with patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP") as mock_smtp:
            mock_connection = MagicMock()
            mock_smtp.return_value = mock_connection

            connector = SMTPConnector(smtp_config)
            connector.connect()

            result = connector.send_email(
                from_address="sender@example.com",
                to=["recipient@example.com"],
                subject="Test Subject",
                body="Test body",
                reply_to="replies@example.com",
            )

            assert result is True
            call_args = mock_connection.sendmail.call_args
            msg_str = call_args[0][2]
            assert "Reply-To: replies@example.com" in msg_str

    def test_send_email_with_from_name(self, smtp_config: SMTPConfig) -> None:
        """Test sending email with display name."""
        with patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP") as mock_smtp:
            mock_connection = MagicMock()
            mock_smtp.return_value = mock_connection

            connector = SMTPConnector(smtp_config)
            connector.connect()

            result = connector.send_email(
                from_address="sender@example.com",
                to=["recipient@example.com"],
                subject="Test Subject",
                body="Test body",
                from_name="Atlas",
            )

            assert result is True
            call_args = mock_connection.sendmail.call_args
            # Envelope should use plain email address
            assert call_args[0][0] == "sender@example.com"
            # Message header should include display name
            msg_str = call_args[0][2]
            assert "From: Atlas <sender@example.com>" in msg_str

    def test_send_email_with_single_attachment(self, smtp_config: SMTPConfig) -> None:
        """Test sending email with a single attachment."""
        with patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP") as mock_smtp:
            mock_connection = MagicMock()
            mock_smtp.return_value = mock_connection

            connector = SMTPConnector(smtp_config)
            connector.connect()

            attachment = OutgoingAttachment(
                filename="test.txt",
                content=b"Hello, attachment!",
                mime_type="text/plain",
            )

            result = connector.send_email(
                from_address="sender@example.com",
                to=["recipient@example.com"],
                subject="Test with attachment",
                body="See attachment",
                attachments=[attachment],
            )

            assert result is True
            call_args = mock_connection.sendmail.call_args
            msg_str = call_args[0][2]
            assert "Content-Disposition: attachment" in msg_str
            assert 'filename="test.txt"' in msg_str
            assert "Content-Type: text/plain" in msg_str

    def test_send_email_with_multiple_attachments(self, smtp_config: SMTPConfig) -> None:
        """Test sending email with multiple attachments."""
        with patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP") as mock_smtp:
            mock_connection = MagicMock()
            mock_smtp.return_value = mock_connection

            connector = SMTPConnector(smtp_config)
            connector.connect()

            attachments = [
                OutgoingAttachment(
                    filename="doc.pdf",
                    content=b"%PDF-1.4 fake pdf content",
                    mime_type="application/pdf",
                ),
                OutgoingAttachment(
                    filename="image.png",
                    content=b"\x89PNG fake png content",
                    mime_type="image/png",
                ),
            ]

            result = connector.send_email(
                from_address="sender@example.com",
                to=["recipient@example.com"],
                subject="Multiple attachments",
                body="See attachments",
                attachments=attachments,
            )

            assert result is True
            call_args = mock_connection.sendmail.call_args
            msg_str = call_args[0][2]
            assert 'filename="doc.pdf"' in msg_str
            assert 'filename="image.png"' in msg_str
            assert "Content-Type: application/pdf" in msg_str
            assert "Content-Type: image/png" in msg_str

    def test_send_email_with_path_attachment(self, smtp_config: SMTPConfig, tmp_path) -> None:
        """Test sending email with file path attachment."""
        with patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP") as mock_smtp:
            mock_connection = MagicMock()
            mock_smtp.return_value = mock_connection

            # Create a temp file
            file_path = tmp_path / "report.csv"
            file_path.write_bytes(b"name,value\ntest,123")

            connector = SMTPConnector(smtp_config)
            connector.connect()

            attachment = OutgoingAttachment(
                filename="report.csv",
                path=str(file_path),
                mime_type="text/csv",
            )

            result = connector.send_email(
                from_address="sender@example.com",
                to=["recipient@example.com"],
                subject="Report attached",
                body="See report",
                attachments=[attachment],
            )

            assert result is True
            call_args = mock_connection.sendmail.call_args
            msg_str = call_args[0][2]
            assert 'filename="report.csv"' in msg_str
            assert "Content-Type: text/csv" in msg_str

    def test_send_email_with_binary_attachment(self, smtp_config: SMTPConfig) -> None:
        """Test sending email with binary attachment is base64 encoded."""
        with patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP") as mock_smtp:
            mock_connection = MagicMock()
            mock_smtp.return_value = mock_connection

            connector = SMTPConnector(smtp_config)
            connector.connect()

            # Binary content
            binary_content = bytes(range(256))
            attachment = OutgoingAttachment(
                filename="binary.bin",
                content=binary_content,
                mime_type="application/octet-stream",
            )

            result = connector.send_email(
                from_address="sender@example.com",
                to=["recipient@example.com"],
                subject="Binary file",
                body="Binary attachment test",
                attachments=[attachment],
            )

            assert result is True
            call_args = mock_connection.sendmail.call_args
            msg_str = call_args[0][2]
            # Check for base64 encoding header
            assert "Content-Transfer-Encoding: base64" in msg_str
            assert 'filename="binary.bin"' in msg_str

    def test_send_email_empty_attachments_list(self, smtp_config: SMTPConfig) -> None:
        """Test sending email with empty attachments list works."""
        with patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP") as mock_smtp:
            mock_connection = MagicMock()
            mock_smtp.return_value = mock_connection

            connector = SMTPConnector(smtp_config)
            connector.connect()

            result = connector.send_email(
                from_address="sender@example.com",
                to=["recipient@example.com"],
                subject="No attachments",
                body="Test body",
                attachments=[],
            )

            assert result is True

    def test_send_email_none_attachments(self, smtp_config: SMTPConfig) -> None:
        """Test sending email with None attachments works (backwards compat)."""
        with patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP") as mock_smtp:
            mock_connection = MagicMock()
            mock_smtp.return_value = mock_connection

            connector = SMTPConnector(smtp_config)
            connector.connect()

            result = connector.send_email(
                from_address="sender@example.com",
                to=["recipient@example.com"],
                subject="No attachments",
                body="Test body",
                attachments=None,
            )

            assert result is True

    def test_header_injection_newline_in_from(self, smtp_config: SMTPConfig) -> None:
        """Test that newline in from_address raises ValueError."""
        with patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP") as mock_smtp:
            mock_connection = MagicMock()
            mock_smtp.return_value = mock_connection

            connector = SMTPConnector(smtp_config)
            connector.connect()

            with pytest.raises(ValueError):
                connector.send_email(
                    from_address="evil@example.com\nBcc: attacker@evil.com",
                    to=["recipient@example.com"],
                    subject="Test",
                    body="Test",
                )

    def test_header_injection_cr_in_from(self, smtp_config: SMTPConfig) -> None:
        """Test that carriage return in from_address raises ValueError."""
        with patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP") as mock_smtp:
            mock_connection = MagicMock()
            mock_smtp.return_value = mock_connection

            connector = SMTPConnector(smtp_config)
            connector.connect()

            with pytest.raises(ValueError):
                connector.send_email(
                    from_address="evil@example.com\rBcc: attacker@evil.com",
                    to=["recipient@example.com"],
                    subject="Test",
                    body="Test",
                )

    def test_header_injection_crlf_in_from(self, smtp_config: SMTPConfig) -> None:
        """Test that CRLF in from_address raises ValueError."""
        with patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP") as mock_smtp:
            mock_connection = MagicMock()
            mock_smtp.return_value = mock_connection

            connector = SMTPConnector(smtp_config)
            connector.connect()

            with pytest.raises(ValueError):
                connector.send_email(
                    from_address="evil@example.com\r\nBcc: attacker@evil.com",
                    to=["recipient@example.com"],
                    subject="Test",
                    body="Test",
                )

    def test_header_injection_newline_in_to(self, smtp_config: SMTPConfig) -> None:
        """Test that newline in to address raises ValueError."""
        with patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP") as mock_smtp:
            mock_connection = MagicMock()
            mock_smtp.return_value = mock_connection

            connector = SMTPConnector(smtp_config)
            connector.connect()

            with pytest.raises(ValueError):
                connector.send_email(
                    from_address="sender@example.com",
                    to=["evil@example.com\nBcc: attacker@evil.com"],
                    subject="Test",
                    body="Test",
                )

    def test_header_injection_newline_in_cc(self, smtp_config: SMTPConfig) -> None:
        """Test that newline in cc address raises ValueError."""
        with patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP") as mock_smtp:
            mock_connection = MagicMock()
            mock_smtp.return_value = mock_connection

            connector = SMTPConnector(smtp_config)
            connector.connect()

            with pytest.raises(ValueError):
                connector.send_email(
                    from_address="sender@example.com",
                    to=["recipient@example.com"],
                    subject="Test",
                    body="Test",
                    cc=["evil@example.com\nBcc: attacker@evil.com"],
                )

    def test_header_injection_newline_in_reply_to(self, smtp_config: SMTPConfig) -> None:
        """Test that newline in reply_to raises ValueError."""
        with patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP") as mock_smtp:
            mock_connection = MagicMock()
            mock_smtp.return_value = mock_connection

            connector = SMTPConnector(smtp_config)
            connector.connect()

            with pytest.raises(ValueError):
                connector.send_email(
                    from_address="sender@example.com",
                    to=["recipient@example.com"],
                    subject="Test",
                    body="Test",
                    reply_to="evil@example.com\nBcc: attacker@evil.com",
                )

    def test_header_injection_multiple_to_one_bad(self, smtp_config: SMTPConfig) -> None:
        """Test that one bad address among multiple to recipients raises ValueError."""
        with patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP") as mock_smtp:
            mock_connection = MagicMock()
            mock_smtp.return_value = mock_connection

            connector = SMTPConnector(smtp_config)
            connector.connect()

            with pytest.raises(ValueError):
                connector.send_email(
                    from_address="sender@example.com",
                    to=["good@example.com", "evil@example.com\nBcc: attacker@evil.com"],
                    subject="Test",
                    body="Test",
                )

    def test_header_injection_null_byte_in_address(self, smtp_config: SMTPConfig) -> None:
        """Test that null byte in email address raises ValueError."""
        with patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP") as mock_smtp:
            mock_connection = MagicMock()
            mock_smtp.return_value = mock_connection

            connector = SMTPConnector(smtp_config)
            connector.connect()

            with pytest.raises(ValueError):
                connector.send_email(
                    from_address="evil@example.com\0Bcc: attacker@evil.com",
                    to=["recipient@example.com"],
                    subject="Test",
                    body="Test",
                )

    def test_header_injection_newline_in_from_name(self, smtp_config: SMTPConfig) -> None:
        """Test that newline in from_name raises ValueError."""
        with patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP") as mock_smtp:
            mock_connection = MagicMock()
            mock_smtp.return_value = mock_connection

            connector = SMTPConnector(smtp_config)
            connector.connect()

            with pytest.raises(ValueError):
                connector.send_email(
                    from_address="sender@example.com",
                    to=["recipient@example.com"],
                    subject="Test",
                    body="Test",
                    from_name="Evil\nBcc: attacker@evil.com",
                )


class TestSMTPConnectorBuildMessage:
    @pytest.fixture
    def smtp_config(self) -> SMTPConfig:
        return SMTPConfig(
            host="smtp.example.com",
            port=587,
            username="user@example.com",
            password=SecretStr("password123"),
            ssl=False,
        )

    def test_build_message_basic(self, smtp_config: SMTPConfig) -> None:
        connector = SMTPConnector(smtp_config)

        msg = connector.build_message(
            from_address="sender@example.com",
            to=["recipient@example.com"],
            subject="Test Subject",
            body="Test body",
        )

        assert msg["From"] == "sender@example.com"
        assert msg["To"] == "recipient@example.com"
        assert msg["Subject"] == "Test Subject"
        assert "Test body" in msg.as_string()

    def test_build_message_with_from_name(self, smtp_config: SMTPConfig) -> None:
        connector = SMTPConnector(smtp_config)

        msg = connector.build_message(
            from_address="sender@example.com",
            to=["recipient@example.com"],
            subject="Test",
            body="Body",
            from_name="Atlas",
        )

        assert msg["From"] == "Atlas <sender@example.com>"

    def test_build_message_with_cc(self, smtp_config: SMTPConfig) -> None:
        connector = SMTPConnector(smtp_config)

        msg = connector.build_message(
            from_address="sender@example.com",
            to=["recipient@example.com"],
            subject="Test",
            body="Body",
            cc=["cc1@example.com", "cc2@example.com"],
        )

        assert msg["Cc"] == "cc1@example.com, cc2@example.com"

    def test_build_message_with_reply_to(self, smtp_config: SMTPConfig) -> None:
        connector = SMTPConnector(smtp_config)

        msg = connector.build_message(
            from_address="sender@example.com",
            to=["recipient@example.com"],
            subject="Test",
            body="Body",
            reply_to="replies@example.com",
        )

        assert msg["Reply-To"] == "replies@example.com"

    def test_build_message_with_attachment(self, smtp_config: SMTPConfig) -> None:
        connector = SMTPConnector(smtp_config)

        attachment = OutgoingAttachment(
            filename="test.txt",
            content=b"file content",
            mime_type="text/plain",
        )

        msg = connector.build_message(
            from_address="sender@example.com",
            to=["recipient@example.com"],
            subject="Test",
            body="Body",
            attachments=[attachment],
        )

        msg_str = msg.as_string()
        assert 'filename="test.txt"' in msg_str
        assert "Content-Type: text/plain" in msg_str

    def test_attachment_filename_directory_traversal_stripped(
        self, smtp_config: SMTPConfig
    ) -> None:
        """Test that directory traversal characters are stripped from attachment filenames."""
        with patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP") as mock_smtp:
            mock_connection = MagicMock()
            mock_smtp.return_value = mock_connection

            connector = SMTPConnector(smtp_config)
            connector.connect()

            attachment = OutgoingAttachment(
                filename="../../etc/passwd",
                content=b"malicious content",
                mime_type="application/octet-stream",
            )

            result = connector.send_email(
                from_address="sender@example.com",
                to=["recipient@example.com"],
                subject="Test",
                body="Body",
                attachments=[attachment],
            )

            assert result is True
            call_args = mock_connection.sendmail.call_args
            msg_str = call_args[0][2]
            assert 'filename="passwd"' in msg_str

    def test_attachment_filename_absolute_path_stripped(self, smtp_config: SMTPConfig) -> None:
        """Test that absolute paths are stripped from attachment filenames."""
        with patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP") as mock_smtp:
            mock_connection = MagicMock()
            mock_smtp.return_value = mock_connection

            connector = SMTPConnector(smtp_config)
            connector.connect()

            attachment = OutgoingAttachment(
                filename="/etc/passwd",
                content=b"malicious content",
                mime_type="application/octet-stream",
            )

            result = connector.send_email(
                from_address="sender@example.com",
                to=["recipient@example.com"],
                subject="Test",
                body="Body",
                attachments=[attachment],
            )

            assert result is True
            call_args = mock_connection.sendmail.call_args
            msg_str = call_args[0][2]
            assert 'filename="passwd"' in msg_str

    def test_attachment_filename_windows_traversal_stripped(self, smtp_config: SMTPConfig) -> None:
        """Test Windows-style path traversal in attachment filenames.

        On macOS/Linux, os.path.basename does not treat backslash as a
        separator, so the full string is kept as the basename.
        """
        with patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP") as mock_smtp:
            mock_connection = MagicMock()
            mock_smtp.return_value = mock_connection

            connector = SMTPConnector(smtp_config)
            connector.connect()

            attachment = OutgoingAttachment(
                filename="..\\..\\Windows\\system.ini",
                content=b"malicious content",
                mime_type="application/octet-stream",
            )

            result = connector.send_email(
                from_address="sender@example.com",
                to=["recipient@example.com"],
                subject="Test",
                body="Body",
                attachments=[attachment],
            )

            assert result is True
            call_args = mock_connection.sendmail.call_args
            msg_str = call_args[0][2]
            # On POSIX, backslash is not a path separator, so basename
            # returns the entire string unchanged.  The MIME library
            # escapes backslashes in the Content-Disposition header, so
            # we verify the filename hasn't been truncated (it still
            # contains "Windows" and "system.ini").
            assert "system.ini" in msg_str
            assert "Windows" in msg_str

    def test_attachment_filename_normal_unchanged(self, smtp_config: SMTPConfig) -> None:
        """Test that a normal filename is not altered by sanitization."""
        with patch("read_no_evil_mcp.email.connectors.smtp.smtplib.SMTP") as mock_smtp:
            mock_connection = MagicMock()
            mock_smtp.return_value = mock_connection

            connector = SMTPConnector(smtp_config)
            connector.connect()

            attachment = OutgoingAttachment(
                filename="report.pdf",
                content=b"%PDF-1.4 content",
                mime_type="application/pdf",
            )

            result = connector.send_email(
                from_address="sender@example.com",
                to=["recipient@example.com"],
                subject="Test",
                body="Body",
                attachments=[attachment],
            )

            assert result is True
            call_args = mock_connection.sendmail.call_args
            msg_str = call_args[0][2]
            assert 'filename="report.pdf"' in msg_str

    def test_build_message_rejects_header_injection(self, smtp_config: SMTPConfig) -> None:
        connector = SMTPConnector(smtp_config)

        with pytest.raises(ValueError):
            connector.build_message(
                from_address="evil@example.com\nBcc: attacker@evil.com",
                to=["recipient@example.com"],
                subject="Test",
                body="Body",
            )


class TestHeaderInjectionEdgeCases:
    @pytest.fixture
    def smtp_config(self) -> SMTPConfig:
        return SMTPConfig(
            host="smtp.example.com",
            port=587,
            username="user@example.com",
            password=SecretStr("password123"),
            ssl=False,
        )

    def test_unicode_line_separator_allowed(self, smtp_config: SMTPConfig) -> None:
        connector = SMTPConnector(smtp_config)
        msg = connector.build_message(
            from_address="sender@example.com",
            to=["recipient@example.com"],
            subject="test\u2028subject",
            body="Body",
        )
        assert msg["Subject"] == "test\u2028subject"

    def test_unicode_paragraph_separator_allowed(self, smtp_config: SMTPConfig) -> None:
        connector = SMTPConnector(smtp_config)
        msg = connector.build_message(
            from_address="sender@example.com",
            to=["recipient@example.com"],
            subject="test\u2029subject",
            body="Body",
        )
        assert msg["Subject"] == "test\u2029subject"

    def test_subject_allows_special_characters(self, smtp_config: SMTPConfig) -> None:
        connector = SMTPConnector(smtp_config)
        subject = "Meeting \U0001f4c5 with caf\u00e9 \u2603"
        msg = connector.build_message(
            from_address="sender@example.com",
            to=["recipient@example.com"],
            subject=subject,
            body="Body",
        )
        assert msg["Subject"] == subject

    def test_from_name_with_newline_rejected(self, smtp_config: SMTPConfig) -> None:
        connector = SMTPConnector(smtp_config)
        with pytest.raises(ValueError):
            connector.build_message(
                from_address="sender@example.com",
                to=["recipient@example.com"],
                subject="Test",
                body="Body",
                from_name="Evil\nBcc: attacker@evil.com",
            )
