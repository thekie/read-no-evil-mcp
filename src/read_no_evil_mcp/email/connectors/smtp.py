"""SMTP connector for sending emails using smtplib."""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import parseaddr

from read_no_evil_mcp.models import SMTPConfig


class SMTPConnector:
    """Connector for sending emails via SMTP using smtplib."""

    def __init__(self, config: SMTPConfig) -> None:
        """Initialize SMTP connector.

        Args:
            config: SMTP server configuration.
        """
        self.config = config
        self._connection: smtplib.SMTP | smtplib.SMTP_SSL | None = None

    def connect(self) -> None:
        """Establish connection to SMTP server."""
        if self.config.ssl:
            self._connection = smtplib.SMTP_SSL(self.config.host, self.config.port)
        else:
            self._connection = smtplib.SMTP(self.config.host, self.config.port)
            self._connection.starttls()

        self._connection.login(
            self.config.username,
            self.config.password.get_secret_value(),
        )

    def disconnect(self) -> None:
        """Close connection to SMTP server."""
        if self._connection:
            self._connection.quit()
            self._connection = None

    def __enter__(self) -> "SMTPConnector":
        """Enter context manager, connecting to the server."""
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit context manager, disconnecting from the server."""
        self.disconnect()

    def send_email(
        self,
        from_addr: str,
        to: list[str],
        subject: str,
        body: str,
        cc: list[str] | None = None,
        reply_to: str | None = None,
    ) -> bool:
        """Send an email.

        Args:
            from_addr: Sender email address.
            to: List of recipient email addresses.
            subject: Email subject line.
            body: Email body text (plain text).
            cc: Optional list of CC recipients.
            reply_to: Optional Reply-To email address.

        Returns:
            True if email was sent successfully.

        Raises:
            RuntimeError: If not connected to SMTP server.
            smtplib.SMTPException: If sending fails.
        """
        if not self._connection:
            raise RuntimeError("Not connected. Call connect() first.")

        msg = MIMEMultipart()
        msg["From"] = from_addr
        msg["To"] = ", ".join(to)
        msg["Subject"] = subject

        if cc:
            msg["Cc"] = ", ".join(cc)

        if reply_to:
            msg["Reply-To"] = reply_to

        msg.attach(MIMEText(body, "plain"))

        # Build recipient list (to + cc)
        recipients = list(to)
        if cc:
            recipients.extend(cc)

        # Extract just the email address for SMTP envelope (from_addr may include display name)
        _, envelope_from = parseaddr(from_addr)
        self._connection.sendmail(envelope_from, recipients, msg.as_string())
        return True
