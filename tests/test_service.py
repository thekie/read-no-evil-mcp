"""Tests for EmailService."""

from datetime import date, datetime, timedelta
from unittest.mock import MagicMock

from read_no_evil_mcp.models import Email, EmailAddress, EmailSummary, Folder
from read_no_evil_mcp.service import EmailService


class TestEmailService:
    def test_connect(self):
        """Test that connect delegates to connector."""
        mock_connector = MagicMock()
        service = EmailService(mock_connector)

        service.connect()

        mock_connector.connect.assert_called_once()

    def test_disconnect(self):
        """Test that disconnect delegates to connector."""
        mock_connector = MagicMock()
        service = EmailService(mock_connector)

        service.disconnect()

        mock_connector.disconnect.assert_called_once()

    def test_list_folders(self):
        """Test listing folders through service."""
        mock_connector = MagicMock()
        expected_folders = [
            Folder(name="INBOX"),
            Folder(name="Sent"),
            Folder(name="Drafts"),
        ]
        mock_connector.list_folders.return_value = expected_folders

        service = EmailService(mock_connector)
        folders = service.list_folders()

        assert folders == expected_folders
        mock_connector.list_folders.assert_called_once()

    def test_fetch_emails(self):
        """Test fetching email summaries through service."""
        mock_connector = MagicMock()
        expected_emails = [
            EmailSummary(
                uid=1,
                folder="INBOX",
                subject="Test 1",
                sender=EmailAddress(address="sender@example.com"),
                date=datetime(2026, 2, 3, 12, 0, 0),
            ),
            EmailSummary(
                uid=2,
                folder="INBOX",
                subject="Test 2",
                sender=EmailAddress(address="sender2@example.com"),
                date=datetime(2026, 2, 2, 12, 0, 0),
            ),
        ]
        mock_connector.fetch_emails.return_value = expected_emails

        service = EmailService(mock_connector)
        emails = service.fetch_emails(
            "INBOX",
            lookback=timedelta(days=7),
            from_date=date(2026, 2, 3),
            limit=10,
        )

        assert emails == expected_emails
        mock_connector.fetch_emails.assert_called_once_with(
            "INBOX",
            lookback=timedelta(days=7),
            from_date=date(2026, 2, 3),
            limit=10,
        )

    def test_fetch_emails_defaults(self):
        """Test fetch_emails with default folder."""
        mock_connector = MagicMock()
        mock_connector.fetch_emails.return_value = []

        service = EmailService(mock_connector)
        service.fetch_emails(lookback=timedelta(days=7))

        mock_connector.fetch_emails.assert_called_once_with(
            "INBOX",
            lookback=timedelta(days=7),
            from_date=None,
            limit=None,
        )

    def test_get_email(self):
        """Test getting full email through service."""
        mock_connector = MagicMock()
        expected_email = Email(
            uid=123,
            folder="INBOX",
            subject="Test Email",
            sender=EmailAddress(address="sender@example.com"),
            date=datetime(2026, 2, 3, 12, 0, 0),
            body_plain="Hello, World!",
        )
        mock_connector.get_email.return_value = expected_email

        service = EmailService(mock_connector)
        email = service.get_email("INBOX", 123)

        assert email == expected_email
        mock_connector.get_email.assert_called_once_with("INBOX", 123)

    def test_get_email_not_found(self):
        """Test getting non-existent email returns None."""
        mock_connector = MagicMock()
        mock_connector.get_email.return_value = None

        service = EmailService(mock_connector)
        email = service.get_email("INBOX", 999)

        assert email is None
        mock_connector.get_email.assert_called_once_with("INBOX", 999)

    def test_context_manager(self):
        """Test that service can be used as context manager."""
        mock_connector = MagicMock()
        mock_connector.list_folders.return_value = [Folder(name="INBOX")]

        with EmailService(mock_connector) as service:
            folders = service.list_folders()

        assert len(folders) == 1
        mock_connector.connect.assert_called_once()
        mock_connector.disconnect.assert_called_once()

    def test_context_manager_disconnects_on_exception(self):
        """Test that context manager disconnects even on exception."""
        mock_connector = MagicMock()
        mock_connector.list_folders.side_effect = RuntimeError("Error")

        try:
            with EmailService(mock_connector) as service:
                service.list_folders()
        except RuntimeError:
            pass

        mock_connector.connect.assert_called_once()
        mock_connector.disconnect.assert_called_once()
