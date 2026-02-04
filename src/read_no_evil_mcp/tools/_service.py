"""Shared service creation helper for tools."""

from functools import lru_cache

from pydantic import SecretStr

from read_no_evil_mcp.accounts.credentials.base import CredentialBackend
from read_no_evil_mcp.accounts.credentials.env import EnvCredentialBackend
from read_no_evil_mcp.accounts.service import AccountService
from read_no_evil_mcp.config import Settings
from read_no_evil_mcp.exceptions import ConfigError
from read_no_evil_mcp.mailbox import SecureMailbox


class LegacyCredentialBackend(CredentialBackend):
    """Credential backend for legacy single-account configuration.

    Returns the password from Settings.imap_password for the "default" account.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def get_password(self, account_id: str) -> SecretStr:
        if account_id == "default" and self._settings.imap_password:
            return self._settings.imap_password

        # For non-default accounts or if password not set, try env backend
        env_backend = EnvCredentialBackend()
        return env_backend.get_password(account_id)


@lru_cache
def get_account_service() -> AccountService:
    """Get or create the account service singleton.

    Returns:
        AccountService instance configured from settings.

    Raises:
        ConfigError: If no accounts are configured.
    """
    settings = Settings()  # type: ignore[call-arg]
    accounts = settings.get_effective_accounts()

    if not accounts:
        raise ConfigError(
            "No accounts configured. Set either multi-account configuration via "
            "YAML config file, or legacy environment variables "
            "(RNOE_IMAP_HOST, RNOE_IMAP_USERNAME, RNOE_IMAP_PASSWORD)."
        )

    # Use legacy backend if using old-style config, otherwise use env backend
    if settings.imap_password and not settings.accounts:
        credentials: CredentialBackend = LegacyCredentialBackend(settings)
    else:
        credentials = EnvCredentialBackend()

    return AccountService(accounts, credentials)


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
