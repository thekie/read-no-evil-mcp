"""Abstract base class for email connectors."""

from abc import ABC, abstractmethod
from datetime import date, timedelta
from types import TracebackType

from read_no_evil_mcp.email.models import Email, EmailSummary, Folder, OutgoingAttachment


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
    def move_email(self, folder: str, uid: int, target_folder: str) -> bool:
        """Move an email to a target folder.

        Args:
            folder: Folder/mailbox containing the email
            uid: Unique identifier of the email
            target_folder: Destination folder to move the email to

        Returns:
            True if successful, False if email not found.
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

    def can_send(self) -> bool:
        """Check if this connector supports sending emails.

        Override this method to return True in connectors that support sending.

        Returns:
            True if send() is supported, False otherwise.
        """
        return False

    def send(
        self,
        from_address: str,
        to: list[str],
        subject: str,
        body: str,
        from_name: str | None = None,
        cc: list[str] | None = None,
        reply_to: str | None = None,
        attachments: list[OutgoingAttachment] | None = None,
    ) -> bool:
        """Send an email (optional capability).

        This is an optional method. Connectors that support sending emails
        should override this method and can_send() to return True.

        Args:
            from_address: Sender email address (e.g., "user@example.com").
            to: List of recipient email addresses.
            subject: Email subject line.
            body: Email body text (plain text).
            from_name: Optional display name for sender (e.g., "Atlas").
            cc: Optional list of CC recipients.
            reply_to: Optional Reply-To email address.
            attachments: Optional list of file attachments.

        Returns:
            True if email was sent successfully.

        Raises:
            NotImplementedError: If the connector doesn't support sending.
        """
        raise NotImplementedError(f"{self.__class__.__name__} does not support sending emails")

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
