"""Secure mailbox that wraps EmailService with protection layer."""

from datetime import date, timedelta
from types import TracebackType

from read_no_evil_mcp.email.service import EmailService
from read_no_evil_mcp.models import Email, EmailSummary, Folder, ScanResult
from read_no_evil_mcp.protection.layer import ProtectionLayer


class PromptInjectionError(Exception):
    """Raised when prompt injection is detected in email content."""

    def __init__(self, scan_result: ScanResult, email_uid: int, folder: str) -> None:
        self.scan_result = scan_result
        self.email_uid = email_uid
        self.folder = folder
        patterns = ", ".join(scan_result.detected_patterns)
        super().__init__(
            f"Prompt injection detected in email {folder}/{email_uid}. "
            f"Detected patterns: {patterns}"
        )


class SecureMailbox:
    """Secure email access with prompt injection protection.

    Wraps EmailService and scans email content before returning it.
    Blocks emails that contain detected prompt injection attacks.
    """

    def __init__(
        self,
        email_service: EmailService,
        protection: ProtectionLayer | None = None,
    ) -> None:
        """Initialize secure mailbox.

        Args:
            email_service: Email service for fetching emails.
            protection: Protection layer for scanning. Defaults to standard layer.
        """
        self._service = email_service
        self._protection = protection or ProtectionLayer()

    def connect(self) -> None:
        """Connect to the email server."""
        self._service.connect()

    def disconnect(self) -> None:
        """Disconnect from the email server."""
        self._service.disconnect()

    def __enter__(self) -> "SecureMailbox":
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
        return self._service.list_folders()

    def fetch_emails(
        self,
        folder: str = "INBOX",
        *,
        lookback: timedelta,
        from_date: date | None = None,
        limit: int | None = None,
    ) -> list[EmailSummary]:
        """Fetch email summaries from a folder.

        Summaries are considered safe (no full body content).

        Args:
            folder: Folder to fetch from (default: INBOX)
            lookback: How far back to look
            from_date: Starting point for lookback (default: today)
            limit: Maximum number of emails to return

        Returns:
            List of EmailSummary objects, newest first.
        """
        return self._service.fetch_emails(
            folder,
            lookback=lookback,
            from_date=from_date,
            limit=limit,
        )

    def get_email(self, folder: str, uid: int) -> Email | None:
        """Get full email content by UID with protection scanning.

        Scans email content for prompt injection attacks before returning.

        Args:
            folder: Folder containing the email
            uid: Unique identifier of the email

        Returns:
            Full Email object or None if not found.

        Raises:
            PromptInjectionError: If prompt injection is detected.
        """
        email = self._service.get_email(folder, uid)

        if email is None:
            return None

        # Scan email content
        scan_result = self._protection.scan_email_content(
            subject=email.subject,
            body_plain=email.body_plain,
            body_html=email.body_html,
        )

        if scan_result.is_blocked:
            raise PromptInjectionError(scan_result, uid, folder)

        return email
