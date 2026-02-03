"""Shared service creation helper for tools."""

from read_no_evil_mcp.config import Settings
from read_no_evil_mcp.email.connectors.imap import IMAPConnector
from read_no_evil_mcp.email.service import EmailService
from read_no_evil_mcp.mailbox import SecureMailbox
from read_no_evil_mcp.models import IMAPConfig


def create_service() -> SecureMailbox:
    """Create a SecureMailbox from environment configuration."""
    settings = Settings()  # type: ignore[call-arg]
    config = IMAPConfig(
        host=settings.imap_host,
        port=settings.imap_port,
        username=settings.imap_username,
        password=settings.imap_password,
        ssl=settings.imap_ssl,
    )
    connector = IMAPConnector(config)
    email_service = EmailService(connector)
    return SecureMailbox(email_service)
