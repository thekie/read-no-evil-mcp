"""Secure mailbox with prompt injection protection and permission enforcement."""

import logging
import re
from datetime import date, timedelta
from functools import lru_cache
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
    get_unscanned_list_prompt,
    get_unscanned_read_prompt,
)
from read_no_evil_mcp.models import FetchResult, SecureEmail, SecureEmailSummary
from read_no_evil_mcp.protection.models import ScanResult
from read_no_evil_mcp.protection.service import ProtectionService

logger = logging.getLogger(__name__)


@lru_cache(maxsize=256)
def _compile_recipient_pattern(pattern: str) -> re.Pattern[str]:
    """Compile and cache a recipient regex pattern (case-insensitive)."""
    return re.compile(pattern, re.IGNORECASE)


class PromptInjectionError(Exception):
    """Raised when prompt injection is detected in email content."""

    def __init__(self, scan_result: ScanResult, email_uid: str, folder: str) -> None:
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
        unscanned_list_prompt: str | None = None,
        unscanned_read_prompt: str | None = None,
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
            unscanned_list_prompt: Custom prompt for unscanned emails in list_emails.
            unscanned_read_prompt: Custom prompt for unscanned emails in get_email.
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
        self._unscanned_list_prompt = unscanned_list_prompt
        self._unscanned_read_prompt = unscanned_read_prompt

    def _get_access_level(self, sender: str, subject: str) -> AccessLevel:
        """Get access level for an email based on sender and subject rules."""
        level = self._access_rules_matcher.get_access_level(sender, subject)
        logger.debug("Access level for sender=%s subject=%r: %s", sender, subject, level.value)
        return level

    def _should_skip_protection(self, sender: str, subject: str) -> bool:
        """Check if protection scanning should be skipped based on access rules."""
        return self._access_rules_matcher.should_skip_protection(sender, subject)

    def _get_list_prompt(self, level: AccessLevel) -> str | None:
        """Get the prompt to show in list_emails for an access level."""
        return get_list_prompt(level, self._list_prompts)

    def _get_read_prompt(self, level: AccessLevel) -> str | None:
        """Get the prompt to show in get_email for an access level."""
        return get_read_prompt(level, self._read_prompts)

    def _get_unscanned_list_prompt(self) -> str:
        """Get the prompt for unscanned emails in list_emails."""
        return get_unscanned_list_prompt(self._unscanned_list_prompt)

    def _get_unscanned_read_prompt(self) -> str:
        """Get the prompt for unscanned emails in get_email."""
        return get_unscanned_read_prompt(self._unscanned_read_prompt)

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

    def _require_allowed_recipients(self, to: list[str], cc: list[str] | None) -> None:
        """Check all recipients against the allowed_recipients patterns.

        Raises PermissionDeniedError if any recipient doesn't match at least one
        allowed pattern.  Skips validation when allowed_recipients is None.
        """
        rules = self._permissions.allowed_recipients
        if rules is None:
            return

        all_recipients = list(to)
        if cc:
            all_recipients.extend(cc)

        for recipient in all_recipients:
            if not any(
                _compile_recipient_pattern(rule.pattern).search(recipient) for rule in rules
            ):
                logger.info("Recipient denied by allowlist (recipient=%s)", recipient)
                raise PermissionDeniedError(
                    f"Recipient '{recipient}' is not in the allowed recipients list"
                )

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
        combined = "\n".join(summary.get_scannable_content().values())
        return self._protection.scan(combined)

    def fetch_emails(
        self,
        folder: str = "INBOX",
        *,
        lookback: timedelta,
        from_date: date | None = None,
        limit: int | None = None,
        offset: int = 0,
        unread_only: bool = False,
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
            unread_only: Only return unread (unseen) emails

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
            unread_only=unread_only,
        )

        secure_summaries: list[SecureEmailSummary] = []
        blocked_count = 0
        hidden_count = 0
        for summary in summaries:
            sender = summary.sender.address
            subject = summary.subject

            # Get access level
            access_level = self._get_access_level(sender, subject)

            # Filter hidden emails
            if access_level == AccessLevel.HIDE:
                hidden_count += 1
                logger.info(
                    "Email hidden by access rules in fetch_emails (uid=%s, folder=%s, subject=%r)",
                    summary.uid,
                    summary.folder,
                    subject,
                )
                continue

            # Check if protection scanning should be skipped
            skip_protection = self._should_skip_protection(sender, subject)
            if skip_protection:
                logger.info(
                    "Protection skipped by rule in fetch_emails (uid=%s, folder=%s, sender=%s)",
                    summary.uid,
                    summary.folder,
                    sender,
                )
            else:
                # Filter by prompt injection scanning
                scan_result = self._scan_summary(summary)
                if scan_result.is_blocked:
                    blocked_count += 1
                    logger.warning(
                        "Prompt injection blocked in fetch_emails "
                        "(uid=%s, folder=%s, subject=%r, score=%.2f, patterns=%s)",
                        summary.uid,
                        summary.folder,
                        subject,
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

            # Build prompt — combine access-level prompt with unscanned prompt
            prompt = self._get_list_prompt(access_level)
            if skip_protection:
                unscanned_prompt = self._get_unscanned_list_prompt()
                prompt = f"{prompt} {unscanned_prompt}" if prompt else unscanned_prompt

            # Build secure summary with access info
            secure_summary = SecureEmailSummary(
                summary=summary,
                access_level=access_level,
                prompt=prompt,
                protection_skipped=skip_protection,
            )
            secure_summaries.append(secure_summary)

        total = len(secure_summaries)
        end = offset + limit if limit is not None else None
        page = secure_summaries[offset:end]

        return FetchResult(
            items=page,
            total=total,
            blocked_count=blocked_count,
            hidden_count=hidden_count,
        )

    def get_email(self, folder: str, uid: str) -> SecureEmail | None:
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

        sender = email.sender.address
        subject = email.subject

        # Get access level
        access_level = self._get_access_level(sender, subject)

        # Check if hidden by access rules
        if access_level == AccessLevel.HIDE:
            logger.info(
                "Email hidden by access rules in get_email (uid=%s, folder=%s, subject=%r)",
                uid,
                folder,
                subject,
            )
            return None

        # Check if protection scanning should be skipped
        skip_protection = self._should_skip_protection(sender, subject)
        if skip_protection:
            logger.info(
                "Protection skipped by rule in get_email (uid=%s, folder=%s, sender=%s)",
                uid,
                folder,
                sender,
            )
        else:
            combined = "\n".join(email.get_scannable_content().values())
            scan_result = self._protection.scan(combined)

            if scan_result.is_blocked:
                logger.warning(
                    "Prompt injection detected in get_email "
                    "(uid=%s, folder=%s, subject=%r, score=%.2f, patterns=%s)",
                    uid,
                    folder,
                    subject,
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

        # Build prompt — combine access-level prompt with unscanned prompt
        prompt = self._get_read_prompt(access_level)
        if skip_protection:
            unscanned_prompt = self._get_unscanned_read_prompt()
            prompt = f"{prompt} {unscanned_prompt}" if prompt else unscanned_prompt

        # Return secure email with access info
        return SecureEmail(
            email=email,
            access_level=access_level,
            prompt=prompt,
            protection_skipped=skip_protection,
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
        self._require_allowed_recipients(to, cc)

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

    def move_email(self, folder: str, uid: str, target_folder: str) -> bool:
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

    def delete_email(self, folder: str, uid: str) -> bool:
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
