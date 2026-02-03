"""Secure mailbox that wraps EmailService with protection service."""

from datetime import date, timedelta
from types import TracebackType

from read_no_evil_mcp.email.service import EmailService
from read_no_evil_mcp.models import Email, EmailSummary, Folder, ScanResult
from read_no_evil_mcp.protection.service import ProtectionService, strip_html_tags


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
        protection: ProtectionService | None = None,
    ) -> None:
        """Initialize secure mailbox.

        Args:
            email_service: Email service for fetching emails.
            protection: Protection service for scanning. Defaults to standard service.
        """
        self._service = email_service
        self._protection = protection or ProtectionService()

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

    def _scan_summary(self, summary: EmailSummary) -> ScanResult:
        """Scan email summary fields for prompt injection.

        Args:
            summary: Email summary to scan.

        Returns:
            ScanResult from scanning subject and sender.
        """
        parts: list[str] = [summary.subject]

        if summary.sender.name:
            parts.append(summary.sender.name)
        parts.append(summary.sender.address)

        combined = "\n".join(parts)
        return self._protection.scan(combined)

    def fetch_emails(
        self,
        folder: str = "INBOX",
        *,
        lookback: timedelta,
        from_date: date | None = None,
        limit: int | None = None,
    ) -> list[EmailSummary]:
        """Fetch email summaries from a folder with protection scanning.

        Scans subject and sender fields for prompt injection.
        Emails with detected attacks are filtered out.

        Args:
            folder: Folder to fetch from (default: INBOX)
            lookback: How far back to look
            from_date: Starting point for lookback (default: today)
            limit: Maximum number of emails to return

        Returns:
            List of safe EmailSummary objects, newest first.
        """
        summaries = self._service.fetch_emails(
            folder,
            lookback=lookback,
            from_date=from_date,
            limit=limit,
        )

        safe_summaries: list[EmailSummary] = []
        for summary in summaries:
            scan_result = self._scan_summary(summary)
            if not scan_result.is_blocked:
                safe_summaries.append(summary)

        return safe_summaries

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

        # Build content to scan: subject, sender, body
        parts: list[str] = [email.subject]

        if email.sender.name:
            parts.append(email.sender.name)
        parts.append(email.sender.address)

        if email.body_plain:
            parts.append(email.body_plain)
        if email.body_html:
            # Always strip HTML tags for better detection
            plain_from_html = strip_html_tags(email.body_html)
            if plain_from_html:
                parts.append(plain_from_html)

        combined = "\n".join(parts)
        scan_result = self._protection.scan(combined)

        if scan_result.is_blocked:
            raise PromptInjectionError(scan_result, uid, folder)

        return email
