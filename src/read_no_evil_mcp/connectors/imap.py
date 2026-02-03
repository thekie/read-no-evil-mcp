"""IMAP connector for reading emails using imap-tools."""

from datetime import date, timedelta

from imap_tools import AND, MailBox

from read_no_evil_mcp.models import (
    Attachment,
    Email,
    EmailAddress,
    EmailSummary,
    Folder,
    IMAPConfig,
)


def _parse_address(addr: tuple[str, str] | None) -> EmailAddress | None:
    """Parse imap-tools address tuple to EmailAddress."""
    if not addr:
        return None
    name, address = addr
    return EmailAddress(name=name or None, address=address)


def _parse_addresses(addrs: tuple[tuple[str, str], ...]) -> list[EmailAddress]:
    """Parse multiple addresses."""
    return [EmailAddress(name=name or None, address=addr) for name, addr in addrs if addr]


class IMAPConnector:
    """Connector for reading emails via IMAP using imap-tools."""

    def __init__(self, config: IMAPConfig) -> None:
        self.config = config
        self._mailbox: MailBox | None = None

    def connect(self) -> None:
        """Establish connection to IMAP server."""
        if self.config.ssl:
            self._mailbox = MailBox(self.config.host, self.config.port)
        else:
            from imap_tools import MailBoxUnencrypted

            self._mailbox = MailBoxUnencrypted(self.config.host, self.config.port)

        self._mailbox.login(
            self.config.username,
            self.config.password.get_secret_value(),
        )

    def disconnect(self) -> None:
        """Close connection to IMAP server."""
        if self._mailbox:
            self._mailbox.logout()
            self._mailbox = None

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
    ) -> list[EmailSummary]:
        """Fetch email summaries from a folder within a time range.

        Args:
            folder: IMAP folder to fetch from (default: INBOX)
            lookback: Required. How far back to look (e.g., timedelta(days=7))
            from_date: Starting point for lookback (default: today)
            limit: Optional max number of emails to return

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

        summaries = []
        for msg in self._mailbox.fetch(criteria, reverse=True, bulk=True):
            sender = _parse_address((msg.from_values.name, msg.from_values.email))
            if not sender:
                sender = EmailAddress(address="unknown@unknown")

            summaries.append(
                EmailSummary(
                    uid=int(msg.uid) if msg.uid else 0,
                    folder=folder,
                    subject=msg.subject or "(no subject)",
                    sender=sender,
                    date=msg.date,
                    has_attachments=len(msg.attachments) > 0,
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
            sender = _parse_address((msg.from_values.name, msg.from_values.email))
            if not sender:
                sender = EmailAddress(address="unknown@unknown")

            attachments = [
                Attachment(
                    filename=att.filename or "unnamed",
                    content_type=att.content_type or "application/octet-stream",
                    size=att.size,
                )
                for att in msg.attachments
            ]

            return Email(
                uid=int(msg.uid) if msg.uid else 0,
                folder=folder,
                subject=msg.subject or "(no subject)",
                sender=sender,
                date=msg.date,
                has_attachments=len(attachments) > 0,
                to=_parse_addresses(msg.to_values),
                cc=_parse_addresses(msg.cc_values),
                body_plain=msg.text or None,
                body_html=msg.html or None,
                attachments=attachments,
                message_id=msg.headers.get("message-id", [None])[0],
            )

        return None

    def __enter__(self) -> "IMAPConnector":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()
