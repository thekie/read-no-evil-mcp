"""Abstract base class for email connectors."""

from abc import ABC, abstractmethod
from datetime import date, timedelta
from types import TracebackType

from read_no_evil_mcp.models import Email, EmailSummary, Folder


class BaseConnector(ABC):
    """Abstract base class defining the interface for email connectors."""

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the email server."""
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to the email server."""
        ...

    @abstractmethod
    def list_folders(self) -> list[Folder]:
        """List all available folders/mailboxes.

        Returns:
            List of Folder objects representing available mailboxes.
        """
        ...

    @abstractmethod
    def fetch_emails(
        self,
        folder: str = "INBOX",
        *,
        lookback: timedelta,
        from_date: date | None = None,
        limit: int | None = None,
    ) -> list[EmailSummary]:
        """Fetch email summaries from a folder within a time range.

        Args:
            folder: Folder/mailbox to fetch from (default: INBOX)
            lookback: How far back to look from from_date
            from_date: Starting point for lookback (default: today)
            limit: Maximum number of emails to return

        Returns:
            List of EmailSummary objects, newest first.
        """
        ...

    @abstractmethod
    def get_email(self, folder: str, uid: int) -> Email | None:
        """Fetch full email content by UID.

        Args:
            folder: Folder/mailbox containing the email
            uid: Unique identifier of the email

        Returns:
            Full Email object or None if not found.
        """
        ...

    @abstractmethod
    def delete_email(self, folder: str, uid: int) -> bool:
        """Delete an email by UID.

        Args:
            folder: Folder/mailbox containing the email
            uid: Unique identifier of the email

        Returns:
            True if email was deleted successfully, False otherwise.
        """
        ...

    def __enter__(self) -> "BaseConnector":
        """Context manager entry - connect to server."""
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Context manager exit - disconnect from server."""
        self.disconnect()
