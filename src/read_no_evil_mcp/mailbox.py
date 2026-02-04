"""Secure mailbox with prompt injection protection and permission enforcement."""

from datetime import date, timedelta
from types import TracebackType

from read_no_evil_mcp.accounts.permissions import AccountPermissions
from read_no_evil_mcp.email.connectors.base import BaseConnector
from read_no_evil_mcp.exceptions import PermissionDeniedError
from read_no_evil_mcp.models import Email, EmailSummary, Folder, ScanResult
from read_no_evil_mcp.protection.service import ProtectionService


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
    """Secure email access with prompt injection protection and permission enforcement.

    Wraps a BaseConnector and scans email content before returning it.
    Blocks emails that contain detected prompt injection attacks.
    Enforces account permissions on all operations.
    """

    def __init__(
        self,
        connector: BaseConnector,
        permissions: AccountPermissions,
        protection: ProtectionService | None = None,
        from_address: str | None = None,
    ) -> None:
        """Initialize secure mailbox.

        Args:
            connector: Email connector for fetching and optionally sending emails.
            permissions: Account permissions to enforce.
            protection: Protection service for scanning. Defaults to standard service.
            from_address: Sender address for outgoing emails.
        """
        self._connector = connector
        self._permissions = permissions
        self._protection = protection or ProtectionService()
        self._from_address = from_address

    def _require_read(self) -> None:
        """Check if read access is allowed.

        Raises:
            PermissionDeniedError: If read access is denied.
        """
        if not self._permissions.read:
            raise PermissionDeniedError("Read access denied for this account")

    def _require_folder(self, folder: str) -> None:
        """Check if access to a specific folder is allowed.

        Args:
            folder: The folder name to check access for.

        Raises:
            PermissionDeniedError: If access to the folder is denied.
        """
        if self._permissions.folders is not None and folder not in self._permissions.folders:
            raise PermissionDeniedError(f"Access to folder '{folder}' denied")

    def _filter_allowed_folders(self, folders: list[Folder]) -> list[Folder]:
        """Filter folders to only include those allowed by permissions.

        Args:
            folders: List of folders to filter.

        Returns:
            List of folders that are allowed by permissions.
        """
        if self._permissions.folders is None:
            return folders
        return [f for f in folders if f.name in self._permissions.folders]

    def _require_send(self) -> None:
        """Check if send access is allowed.

        Raises:
            PermissionDeniedError: If send access is denied.
        """
        if not self._permissions.send:
            raise PermissionDeniedError("Send access denied for this account")

    def connect(self) -> None:
        """Connect to the email server."""
        self._connector.connect()

    def disconnect(self) -> None:
        """Disconnect from the email server."""
        self._connector.disconnect()

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

        Raises:
            PermissionDeniedError: If read access is denied.
        """
        self._require_read()
        folders = self._connector.list_folders()
        return self._filter_allowed_folders(folders)

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

        Raises:
            PermissionDeniedError: If read access is denied or folder is not allowed.
        """
        self._require_read()
        self._require_folder(folder)

        summaries = self._connector.fetch_emails(
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
            PermissionDeniedError: If read access is denied or folder is not allowed.
            PromptInjectionError: If prompt injection is detected.
        """
        self._require_read()
        self._require_folder(folder)

        email = self._connector.get_email(folder, uid)

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
            parts.append(email.body_html)

        combined = "\n".join(parts)
        scan_result = self._protection.scan(combined)

        if scan_result.is_blocked:
            raise PromptInjectionError(scan_result, uid, folder)

        return email

    def send_email(
        self,
        to: list[str],
        subject: str,
        body: str,
        cc: list[str] | None = None,
        reply_to: str | None = None,
    ) -> bool:
        """Send an email.

        Args:
            to: List of recipient email addresses.
            subject: Email subject line.
            body: Email body text (plain text).
            cc: Optional list of CC recipients.
            reply_to: Optional Reply-To email address.

        Returns:
            True if email was sent successfully.

        Raises:
            PermissionDeniedError: If send access is denied.
            RuntimeError: If sending is not supported by the connector.
        """
        self._require_send()

        if not self._connector.can_send():
            raise RuntimeError("Sending not configured for this account")

        if not self._from_address:
            raise RuntimeError("From address not configured for this account")

        return self._connector.send(
            from_addr=self._from_address,
            to=to,
            subject=subject,
            body=body,
            cc=cc,
            reply_to=reply_to,
        )

    def delete_email(self, folder: str, uid: int) -> bool:
        """Delete an email by UID.

        Args:
            folder: Folder containing the email
            uid: Unique identifier of the email

        Returns:
            True if email was deleted successfully, False otherwise.

        Raises:
            PermissionDeniedError: If delete access is denied or folder is not allowed.
        """
        if not self._permissions.delete:
            raise PermissionDeniedError("Delete access denied for this account")
        self._require_folder(folder)

        return self._connector.delete_email(folder, uid)
