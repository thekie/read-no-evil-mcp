"""Tests for SMTPConnector."""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import SecretStr

from read_no_evil_mcp.email.connectors.smtp import SMTPConnector
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
