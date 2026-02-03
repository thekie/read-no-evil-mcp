"""Shared service creation helper for tools."""

from read_no_evil_mcp.config import Settings
from read_no_evil_mcp.connectors.imap import IMAPConnector
from read_no_evil_mcp.models import IMAPConfig
from read_no_evil_mcp.service import EmailService


def create_service() -> EmailService:
    """Create an EmailService from environment configuration."""
    settings = Settings()  # type: ignore[call-arg]
    config = IMAPConfig(
        host=settings.imap_host,
        port=settings.imap_port,
        username=settings.imap_username,
        password=settings.imap_password,
        ssl=settings.imap_ssl,
    )
    connector = IMAPConnector(config)
    return EmailService(connector)
