"""Shared service creation helper for tools."""

from functools import lru_cache

from read_no_evil_mcp.accounts.config import AccountConfig
from read_no_evil_mcp.accounts.credentials.env import EnvCredentialBackend
from read_no_evil_mcp.accounts.service import AccountService
from read_no_evil_mcp.config import Settings
from read_no_evil_mcp.exceptions import ConfigError
from read_no_evil_mcp.mailbox import SecureMailbox


@lru_cache
def get_account_service() -> AccountService:
    """Get or create the account service singleton.

    Returns:
        AccountService instance configured from settings.

    Raises:
        ConfigError: If no accounts are configured.
    """
    settings = Settings()

    if not settings.accounts:
        raise ConfigError("No accounts configured. Configure accounts via YAML config file.")

    return AccountService(
        settings.accounts,
        EnvCredentialBackend(),
        max_attachment_size=settings.max_attachment_size,
        default_threshold=settings.protection.threshold,
    )


def create_securemailbox(account_id: str) -> SecureMailbox:
    """Create a SecureMailbox for the specified account.

    Args:
        account_id: The unique identifier of the account.

    Returns:
        SecureMailbox instance configured for the account.

    Raises:
        AccountNotFoundError: If the account ID is not found.
        CredentialNotFoundError: If credentials cannot be retrieved.
    """
    service = get_account_service()
    return service.get_mailbox(account_id)


def list_configured_accounts() -> list[str]:
    """List all configured account IDs.

    Returns:
        List of account identifiers.
    """
    service = get_account_service()
    return service.list_accounts()


def get_account_config(account_id: str) -> AccountConfig:
    """Get the configuration for an account.

    Args:
        account_id: The unique identifier of the account.

    Returns:
        The account configuration.

    Raises:
        AccountNotFoundError: If the account ID is not found.
    """
    service = get_account_service()
    return service.get_config(account_id)
