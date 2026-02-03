"""IMAP connector for reading emails."""

from read_no_evil_mcp.models import (
    Email,
    EmailSummary,
    Folder,
    IMAPConfig,
)


class IMAPConnector:
    """Connector for reading emails via IMAP."""

    def __init__(self, config: IMAPConfig) -> None:
        self.config = config
        self._connection = None

    def connect(self) -> None:
        """Establish connection to IMAP server."""
        raise NotImplementedError

    def disconnect(self) -> None:
        """Close connection to IMAP server."""
        raise NotImplementedError

    def list_folders(self) -> list[Folder]:
        """List all folders/mailboxes."""
        raise NotImplementedError

    def fetch_emails(
        self,
        folder: str = "INBOX",
        limit: int = 10,
        offset: int = 0,
    ) -> list[EmailSummary]:
        """Fetch email summaries from a folder with pagination."""
        raise NotImplementedError

    def get_email(self, folder: str, uid: int) -> Email:
        """Fetch full email content by UID."""
        raise NotImplementedError

    def __enter__(self) -> "IMAPConnector":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.disconnect()
