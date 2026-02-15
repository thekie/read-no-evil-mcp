"""SMTP connector for sending emails using smtplib."""

import logging
import os
import re
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from read_no_evil_mcp.email.connectors.config import SMTPConfig
from read_no_evil_mcp.email.models import OutgoingAttachment

logger = logging.getLogger(__name__)

_HEADER_INJECTION_RE = re.compile(r"[\r\n\0]")


def _validate_header_value(value: str) -> None:
    """Validate a string is safe from SMTP header injection.

    Raises:
        ValueError: If the value contains newline, carriage return, or null characters.
    """
    if _HEADER_INJECTION_RE.search(value):
        # SECURITY: Do not log the value — it may contain injection payloads
        logger.warning("Header injection attempt detected")
        raise ValueError("Value contains invalid characters (newline, carriage return, or null)")


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
        logger.debug(
            "Connecting to SMTP server (host=%s, port=%s, ssl=%s)",
            self.config.host,
            self.config.port,
            self.config.ssl,
        )
        if self.config.ssl:
            self._connection = smtplib.SMTP_SSL(self.config.host, self.config.port)
        else:
            self._connection = smtplib.SMTP(self.config.host, self.config.port)
            self._connection.starttls()

        self._connection.login(
            self.config.username,
            self.config.password.get_secret_value(),
        )
        logger.info("SMTP connection established (host=%s)", self.config.host)

    def disconnect(self) -> None:
        """Close connection to SMTP server."""
        if self._connection:
            self._connection.quit()
            self._connection = None
            logger.info("SMTP connection closed")

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

    def build_message(
        self,
        from_address: str,
        to: list[str],
        subject: str,
        body: str,
        from_name: str | None = None,
        cc: list[str] | None = None,
        reply_to: str | None = None,
        attachments: list[OutgoingAttachment] | None = None,
    ) -> MIMEMultipart:
        """Build a MIME message with header injection validation.

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
            Composed MIMEMultipart message.

        Raises:
            ValueError: If any header value contains injection characters.
        """
        _validate_header_value(from_address)
        for addr in to:
            _validate_header_value(addr)
        if cc:
            for addr in cc:
                _validate_header_value(addr)
        if reply_to:
            _validate_header_value(reply_to)
        if from_name:
            _validate_header_value(from_name)

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
                safe_filename = os.path.basename(attachment.filename)
                part.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=safe_filename,
                )
                msg.attach(part)

        return msg

    def send_message(
        self, from_address: str, recipients: list[str], message: MIMEMultipart
    ) -> None:
        """Send a pre-built message via SMTP.

        Args:
            from_address: Envelope sender address.
            recipients: List of envelope recipient addresses.
            message: Composed MIME message.

        Raises:
            RuntimeError: If not connected to SMTP server.
            smtplib.SMTPException: If sending fails.
        """
        if not self._connection:
            raise RuntimeError("Not connected. Call connect() first.")

        self._connection.sendmail(from_address, recipients, message.as_string())

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
        msg = self.build_message(
            from_address=from_address,
            to=to,
            subject=subject,
            body=body,
            from_name=from_name,
            cc=cc,
            reply_to=reply_to,
            attachments=attachments,
        )

        recipients = list(to)
        if cc:
            recipients.extend(cc)

        self.send_message(from_address, recipients, msg)
        logger.info("Email sent (recipients=%d, subject=%r)", len(recipients), subject)
        return True
