"""Email service that orchestrates connectors."""

from datetime import date, timedelta
from types import TracebackType

from read_no_evil_mcp.connectors.base import BaseConnector
from read_no_evil_mcp.models import Email, EmailSummary, Folder


class EmailService:
    """Service layer for email operations.

    Orchestrates connector operations and will later integrate
    protection/scanning layers.
    """

    def __init__(self, connector: BaseConnector) -> None:
        """Initialize the service with a connector.

        Args:
            connector: Email connector to use for operations.
        """
        self._connector = connector

    def connect(self) -> None:
        """Connect to the email server."""
        self._connector.connect()

    def disconnect(self) -> None:
        """Disconnect from the email server."""
        self._connector.disconnect()

    def __enter__(self) -> "EmailService":
        """Enter context manager, connecting to the server."""
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit context manager, disconnecting from the server."""
        self.disconnect()

    def list_folders(self) -> list[Folder]:
        """List all available folders.

        Returns:
            List of Folder objects.
        """
        return self._connector.list_folders()

    def fetch_emails(
        self,
        folder: str = "INBOX",
        *,
        lookback: timedelta,
        from_date: date | None = None,
        limit: int | None = None,
    ) -> list[EmailSummary]:
        """Fetch email summaries from a folder.

        Args:
            folder: Folder to fetch from (default: INBOX)
            lookback: How far back to look
            from_date: Starting point for lookback (default: today)
            limit: Maximum number of emails to return

        Returns:
            List of EmailSummary objects, newest first.
        """
        return self._connector.fetch_emails(
            folder,
            lookback=lookback,
            from_date=from_date,
            limit=limit,
        )

    def get_email(self, folder: str, uid: int) -> Email | None:
        """Get full email content by UID.

        Args:
            folder: Folder containing the email
            uid: Unique identifier of the email

        Returns:
            Full Email object or None if not found.
        """
        # Future: Add protection/scanning here before returning
        return self._connector.get_email(folder, uid)
