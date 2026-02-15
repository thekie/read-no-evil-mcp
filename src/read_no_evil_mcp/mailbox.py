"""Secure mailbox with prompt injection protection and permission enforcement."""

import logging
from datetime import date, timedelta
from types import TracebackType

from read_no_evil_mcp.accounts.config import AccessLevel
from read_no_evil_mcp.accounts.permissions import AccountPermissions
from read_no_evil_mcp.defaults import DEFAULT_MAX_ATTACHMENT_SIZE
from read_no_evil_mcp.email.connectors.base import BaseConnector
from read_no_evil_mcp.email.models import (
    EmailSummary,
    Folder,
    OutgoingAttachment,
)
from read_no_evil_mcp.exceptions import PermissionDeniedError
from read_no_evil_mcp.filtering.access_rules import (
    AccessRuleMatcher,
    get_list_prompt,
    get_read_prompt,
)
from read_no_evil_mcp.models import FetchResult, SecureEmail, SecureEmailSummary
from read_no_evil_mcp.protection.models import ScanResult
from read_no_evil_mcp.protection.service import ProtectionService

logger = logging.getLogger(__name__)


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
    """Scans email content for prompt injection before returning it to the agent.

    Blocks emails with detected attacks, enforces per-account permissions,
    and annotates results with access level and prompt from access rules.
    """

    def __init__(
        self,
        connector: BaseConnector,
        permissions: AccountPermissions,
        protection: ProtectionService | None = None,
        from_address: str | None = None,
        from_name: str | None = None,
        access_rules_matcher: AccessRuleMatcher | None = None,
        list_prompts: dict[AccessLevel, str | None] | None = None,
        read_prompts: dict[AccessLevel, str | None] | None = None,
        max_attachment_size: int = DEFAULT_MAX_ATTACHMENT_SIZE,
    ) -> None:
        """Initialize secure mailbox.

        Args:
            connector: Email connector for fetching and optionally sending emails.
            permissions: Account permissions to enforce.
            protection: Protection service for scanning. Defaults to standard service.
            from_address: Sender email address for outgoing emails.
            from_name: Optional display name for sender.
            access_rules_matcher: Matcher for sender/subject access rules.
            list_prompts: Custom prompts for list_emails output per access level.
            read_prompts: Custom prompts for get_email output per access level.
            max_attachment_size: Maximum attachment size in bytes.
        """
        self._connector = connector
        self._permissions = permissions
        self._protection = protection or ProtectionService()
        self._from_address = from_address
        self._from_name = from_name
        self._access_rules_matcher = access_rules_matcher or AccessRuleMatcher()
        self._list_prompts = list_prompts
        self._read_prompts = read_prompts
        self._max_attachment_size = max_attachment_size

    def _get_access_level(self, sender: str, subject: str) -> AccessLevel:
        """Get access level for an email based on sender and subject rules."""
        level = self._access_rules_matcher.get_access_level(sender, subject)
        logger.debug("Access level for sender=%s subject=%r: %s", sender, subject, level.value)
        return level

    def _get_list_prompt(self, level: AccessLevel) -> str | None:
        """Get the prompt to show in list_emails for an access level."""
        return get_list_prompt(level, self._list_prompts)

    def _get_read_prompt(self, level: AccessLevel) -> str | None:
        """Get the prompt to show in get_email for an access level."""
        return get_read_prompt(level, self._read_prompts)

    def _require_read(self) -> None:
        """Check if read access is allowed."""
        if not self._permissions.read:
            logger.info("Read permission denied")
            raise PermissionDeniedError("Read access denied for this account")

    def _require_folder(self, folder: str) -> None:
        """Check if access to a specific folder is allowed."""
        if self._permissions.folders is not None and folder not in self._permissions.folders:
            logger.info("Folder access denied (folder=%s)", folder)
            raise PermissionDeniedError(f"Access to folder '{folder}' denied")

    def _require_move(self) -> None:
        """Check if move access is allowed."""
        if not self._permissions.move:
            logger.info("Move permission denied")
            raise PermissionDeniedError("Move access denied for this account")

    def _filter_allowed_folders(self, folders: list[Folder]) -> list[Folder]:
        """Filter folders to only include those allowed by permissions."""
        if self._permissions.folders is None:
            return folders
        return [f for f in folders if f.name in self._permissions.folders]

    def _require_send(self) -> None:
        """Check if send access is allowed."""
        if not self._permissions.send:
            logger.info("Send permission denied")
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
        """Scan email summary fields for prompt injection."""
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
        offset: int = 0,
    ) -> FetchResult:
        """Fetch email summaries from a folder with protection scanning.

        Scans subject and sender fields for prompt injection.
        Emails with detected attacks or HIDE access level are filtered out.
        Pagination (offset/limit) is applied after filtering.

        Args:
            folder: Folder to fetch from (default: INBOX)
            lookback: How far back to look
            from_date: Starting point for lookback (default: today)
            limit: Maximum number of emails to return
            offset: Number of emails to skip (default: 0)

        Returns:
            FetchResult with paginated items and total count.

        Raises:
            PermissionDeniedError: If read access is denied or folder is not allowed.
        """
        self._require_read()
        self._require_folder(folder)

        summaries = self._connector.fetch_emails(
            folder,
            lookback=lookback,
            from_date=from_date,
        )

        secure_summaries: list[SecureEmailSummary] = []
        for summary in summaries:
            # Filter by prompt injection scanning
            scan_result = self._scan_summary(summary)
            if scan_result.is_blocked:
                logger.warning(
                    "Prompt injection blocked in fetch_emails "
                    "(uid=%s, folder=%s, subject=%r, score=%.2f, patterns=%s)",
                    summary.uid,
                    summary.folder,
                    summary.subject,
                    scan_result.score,
                    scan_result.detected_patterns,
                )
                continue

            logger.debug(
                "Email scan safe (uid=%s, folder=%s, score=%.2f)",
                summary.uid,
                summary.folder,
                scan_result.score,
            )

            # Get access level
            access_level = self._get_access_level(summary.sender.address, summary.subject)

            # Filter hidden emails
            if access_level == AccessLevel.HIDE:
                logger.info(
                    "Email hidden by access rules in fetch_emails (uid=%s, folder=%s, subject=%r)",
                    summary.uid,
                    summary.folder,
                    summary.subject,
                )
                continue

            # Build secure summary with access info
            secure_summary = SecureEmailSummary(
                summary=summary,
                access_level=access_level,
                prompt=self._get_list_prompt(access_level),
            )
            secure_summaries.append(secure_summary)

        total = len(secure_summaries)
        end = offset + limit if limit is not None else None
        page = secure_summaries[offset:end]

        return FetchResult(items=page, total=total)

    def get_email(self, folder: str, uid: int) -> SecureEmail | None:
        """Get full email content by UID with protection scanning.

        Scans email content for prompt injection attacks before returning.

        Args:
            folder: Folder containing the email
            uid: Unique identifier of the email

        Returns:
            SecureEmail object (enriched with access level/prompt) or None if not found.

        Raises:
            PermissionDeniedError: If read access is denied or folder is not allowed.
            PromptInjectionError: If prompt injection is detected.
        """
        self._require_read()
        self._require_folder(folder)

        email = self._connector.get_email(folder, uid)

        if email is None:
            return None

        # Get access level
        access_level = self._get_access_level(email.sender.address, email.subject)

        # Check if hidden by access rules
        if access_level == AccessLevel.HIDE:
            logger.info(
                "Email hidden by access rules in get_email (uid=%s, folder=%s, subject=%r)",
                uid,
                folder,
                email.subject,
            )
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
            logger.warning(
                "Prompt injection detected in get_email "
                "(uid=%s, folder=%s, subject=%r, score=%.2f, patterns=%s)",
                uid,
                folder,
                email.subject,
                scan_result.score,
                scan_result.detected_patterns,
            )
            raise PromptInjectionError(scan_result, uid, folder)

        logger.debug(
            "Email scan safe (uid=%s, folder=%s, score=%.2f)",
            uid,
            folder,
            scan_result.score,
        )

        # Return secure email with access info
        return SecureEmail(
            email=email,
            access_level=access_level,
            prompt=self._get_read_prompt(access_level),
        )

    def send_email(
        self,
        to: list[str],
        subject: str,
        body: str,
        cc: list[str] | None = None,
        reply_to: str | None = None,
        attachments: list[OutgoingAttachment] | None = None,
    ) -> bool:
        """Send an email.

        Args:
            to: List of recipient email addresses.
            subject: Email subject line.
            body: Email body text (plain text).
            cc: Optional list of CC recipients.
            reply_to: Optional Reply-To email address.
            attachments: Optional list of file attachments.

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

        if attachments:
            for attachment in attachments:
                attachment.check_size(max_size=self._max_attachment_size)

        return self._connector.send(
            from_address=self._from_address,
            to=to,
            subject=subject,
            body=body,
            from_name=self._from_name,
            cc=cc,
            reply_to=reply_to,
            attachments=attachments,
        )

    def move_email(self, folder: str, uid: int, target_folder: str) -> bool:
        """Move an email to a target folder.

        Args:
            folder: Folder containing the email
            uid: Unique identifier of the email
            target_folder: Destination folder to move the email to

        Returns:
            True if successful, False if email not found.

        Raises:
            PermissionDeniedError: If move access is denied or folder is not allowed.
        """
        self._require_move()
        self._require_folder(folder)
        self._require_folder(target_folder)

        return self._connector.move_email(folder, uid, target_folder)

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
            logger.info("Delete permission denied")
            raise PermissionDeniedError("Delete access denied for this account")
        self._require_folder(folder)

        return self._connector.delete_email(folder, uid)
