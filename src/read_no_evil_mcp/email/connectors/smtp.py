"""SMTP connector for sending emails using smtplib."""

import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from read_no_evil_mcp.email.connectors.config import SMTPConfig
from read_no_evil_mcp.email.models import OutgoingAttachment


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
        from_address: str,
        to: list[str],
        subject: str,
        body: str,
        from_name: str | None = None,
        cc: list[str] | None = None,
        reply_to: str | None = None,
        attachments: list[OutgoingAttachment] | None = None,
    ) -> bool:
        """Send an email.

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
            RuntimeError: If not connected to SMTP server.
            smtplib.SMTPException: If sending fails.
        """
        if not self._connection:
            raise RuntimeError("Not connected. Call connect() first.")

        msg = MIMEMultipart()
        # Build From header with optional display name
        if from_name:
            msg["From"] = f"{from_name} <{from_address}>"
        else:
            msg["From"] = from_address
        msg["To"] = ", ".join(to)
        msg["Subject"] = subject

        if cc:
            msg["Cc"] = ", ".join(cc)

        if reply_to:
            msg["Reply-To"] = reply_to

        msg.attach(MIMEText(body, "plain"))

        # Add attachments
        if attachments:
            for attachment in attachments:
                content = attachment.get_content()
                maintype, subtype = attachment.mime_type.split("/", 1)
                part = MIMEBase(maintype, subtype)
                part.set_payload(content)
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=attachment.filename,
                )
                msg.attach(part)

        # Build recipient list (to + cc)
        recipients = list(to)
        if cc:
            recipients.extend(cc)

        # Use from_address directly for SMTP envelope (no parsing needed)
        self._connection.sendmail(from_address, recipients, msg.as_string())
        return True
