"""IMAP connector for reading emails using imap-tools."""

import logging
from datetime import date, datetime, timedelta, timezone

from imap_tools import AND, MailBox, MailBoxUnencrypted
from imap_tools import EmailAddress as IMAPEmailAddress

from read_no_evil_mcp.email.connectors.base import BaseConnector
from read_no_evil_mcp.email.connectors.config import IMAPConfig, SMTPConfig
from read_no_evil_mcp.email.connectors.smtp import SMTPConnector
from read_no_evil_mcp.email.models import (
    Attachment,
    Email,
    EmailAddress,
    EmailSummary,
    Folder,
    OutgoingAttachment,
)

logger = logging.getLogger(__name__)

# Default sender for emails without from address
_DEFAULT_SENDER = EmailAddress(address="unknown@unknown")


def _convert_address(addr: IMAPEmailAddress | None) -> EmailAddress:
    """Convert imap-tools EmailAddress to our EmailAddress model."""
    if addr is None or not addr.email:
        return _DEFAULT_SENDER
    return EmailAddress(name=addr.name or None, address=addr.email)


def _convert_addresses(addrs: tuple[IMAPEmailAddress, ...]) -> list[EmailAddress]:
    """Convert tuple of imap-tools EmailAddress to list of our EmailAddress model."""
    return [
        EmailAddress(name=addr.name or None, address=addr.email) for addr in addrs if addr.email
    ]


class IMAPConnector(BaseConnector):
    """Connector for reading emails via IMAP using imap-tools.

    Optionally supports sending emails via SMTP when smtp_config is provided.
    """

    def __init__(
        self,
        config: IMAPConfig,
        smtp_config: SMTPConfig | None = None,
    ) -> None:
        """Initialize IMAP connector.

        Args:
            config: IMAP server configuration.
            smtp_config: Optional SMTP configuration for sending emails.
        """
        self.config = config
        self._mailbox: MailBox | MailBoxUnencrypted | None = None
        self._smtp_config = smtp_config
        self._smtp_connector: SMTPConnector | None = None

    def connect(self) -> None:
        """Establish connection to IMAP server."""
        if self.config.ssl:
            mailbox: MailBox | MailBoxUnencrypted = MailBox(self.config.host, self.config.port)
        else:
            mailbox = MailBoxUnencrypted(self.config.host, self.config.port)

        mailbox.login(
            self.config.username,
            self.config.password.get_secret_value(),
        )
        self._mailbox = mailbox

    def disconnect(self) -> None:
        """Close connection to IMAP server (and SMTP if connected)."""
        if self._mailbox:
            try:
                self._mailbox.logout()
            except Exception:
                logger.debug("IMAP logout failed (connection may already be closed)")
            self._mailbox = None

        if self._smtp_connector:
            self._smtp_connector.disconnect()
            self._smtp_connector = None

    def list_folders(self) -> list[Folder]:
        """List all folders/mailboxes."""
        if not self._mailbox:
            raise RuntimeError("Not connected. Call connect() first.")

        folders = []
        for folder_info in self._mailbox.folder.list():
            folders.append(
                Folder(
                    name=folder_info.name,
                    delimiter=folder_info.delim,
                    flags=list(folder_info.flags),
                )
            )
        return folders

    def fetch_emails(
        self,
        folder: str = "INBOX",
        *,
        lookback: timedelta,
        from_date: date | None = None,
        limit: int | None = None,
        unread_only: bool = False,
    ) -> list[EmailSummary]:
        """Fetch email summaries from a folder within a time range.

        Args:
            folder: IMAP folder to fetch from (default: INBOX)
            lookback: Required. How far back to look (e.g., timedelta(days=7))
            from_date: Starting point for lookback (default: today)
            limit: Optional max number of emails to return
            unread_only: Only return unread (unseen) emails

        Returns:
            List of EmailSummary, newest first
        """
        if not self._mailbox:
            raise RuntimeError("Not connected. Call connect() first.")

        self._mailbox.folder.set(folder)

        # Calculate date range
        end_date = from_date or date.today()
        start_date = end_date - lookback

        # Build IMAP criteria - filter happens server-side
        criteria = AND(date_gte=start_date, date_lt=end_date + timedelta(days=1))
        if unread_only:
            criteria = AND(criteria, seen=False)

        summaries = []
        for msg in self._mailbox.fetch(criteria, mark_seen=False, reverse=True, bulk=True):
            if not msg.uid:
                logger.warning("Skipping email with missing UID (subject=%r)", msg.subject)
                continue

            sender = _convert_address(msg.from_values)

            summaries.append(
                EmailSummary(
                    uid=int(msg.uid),
                    folder=folder,
                    subject=msg.subject or "(no subject)",
                    sender=sender,
                    date=msg.date,
                    has_attachments=len(msg.attachments) > 0,
                    is_seen="\\Seen" in msg.flags,
                )
            )

            if limit and len(summaries) >= limit:
                break

        return summaries

    def get_email(self, folder: str, uid: int) -> Email | None:
        """Fetch full email content by UID."""
        if not self._mailbox:
            raise RuntimeError("Not connected. Call connect() first.")

        self._mailbox.folder.set(folder)

        for msg in self._mailbox.fetch(AND(uid=str(uid))):
            if not msg.uid:
                logger.warning("Skipping email with missing UID (subject=%r)", msg.subject)
                continue

            sender = _convert_address(msg.from_values)

            attachments = [
                Attachment(
                    filename=att.filename or "unnamed",
                    content_type=att.content_type or "application/octet-stream",
                    size=att.size,
                )
                for att in msg.attachments
            ]

            return Email(
                uid=int(msg.uid),
                folder=folder,
                subject=msg.subject or "(no subject)",
                sender=sender,
                date=msg.date,
                has_attachments=len(attachments) > 0,
                is_seen="\\Seen" in msg.flags,
                to=_convert_addresses(msg.to_values),
                cc=_convert_addresses(msg.cc_values),
                body_plain=msg.text or None,
                body_html=msg.html or None,
                attachments=attachments,
                message_id=msg.headers.get("message-id", [None])[0],
            )

        return None

    def move_email(self, folder: str, uid: int, target_folder: str) -> bool:
        """Move an email to a target folder.

        Args:
            folder: Folder/mailbox containing the email
            uid: Unique identifier of the email
            target_folder: Destination folder to move the email to

        Returns:
            True if successful, False if email not found.
        """
        if not self._mailbox:
            raise RuntimeError("Not connected. Call connect() first.")

        self._mailbox.folder.set(folder)

        # Check if email exists
        emails = list(self._mailbox.fetch(AND(uid=str(uid)), mark_seen=False))
        if not emails:
            return False

        # Move email to target folder
        self._mailbox.move(str(uid), target_folder)
        return True

    def delete_email(self, folder: str, uid: int) -> bool:
        """Delete an email by UID.

        Args:
            folder: IMAP folder containing the email
            uid: Unique identifier of the email

        Returns:
            True if email was deleted successfully, False otherwise.
        """
        if not self._mailbox:
            raise RuntimeError("Not connected. Call connect() first.")

        self._mailbox.folder.set(folder)

        self._mailbox.delete(str(uid))
        self._mailbox.expunge()

        return True

    def can_send(self) -> bool:
        """Check if this connector supports sending emails.

        Returns:
            True if SMTP is configured, False otherwise.
        """
        return self._smtp_config is not None

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
        """Send an email via SMTP and save a copy to the Sent folder.

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
            NotImplementedError: If SMTP is not configured.
            RuntimeError: If not connected.
        """
        if not self._smtp_config:
            raise NotImplementedError(
                "IMAPConnector does not support sending emails without SMTP configuration"
            )

        if not self._smtp_connector:
            self._smtp_connector = SMTPConnector(self._smtp_config)
            self._smtp_connector.connect()

        msg = self._smtp_connector.build_message(
            from_address=from_address,
            to=to,
            subject=subject,
            body=body,
            from_name=from_name,
            cc=cc,
            reply_to=reply_to,
            attachments=attachments,
        )

        # Send via SMTP
        recipients = list(to)
        if cc:
            recipients.extend(cc)
        self._smtp_connector.send_message(from_address, recipients, msg)

        # Save to Sent folder via IMAP
        if self.config.sent_folder and self._mailbox:
            self._mailbox.append(
                msg.as_bytes(),
                self.config.sent_folder,
                dt=datetime.now(timezone.utc),
                flag_set=[r"\Seen"],
            )

        return True
