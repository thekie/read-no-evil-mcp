"""Account service for managing multiple email accounts."""

from pydantic import SecretStr

from read_no_evil_mcp.accounts.config import AccountConfig
from read_no_evil_mcp.accounts.credentials.base import CredentialBackend
from read_no_evil_mcp.email.connectors.base import BaseConnector
from read_no_evil_mcp.email.connectors.imap import IMAPConnector
from read_no_evil_mcp.exceptions import AccountNotFoundError, UnsupportedConnectorError
from read_no_evil_mcp.mailbox import SecureMailbox
from read_no_evil_mcp.models import IMAPConfig, SMTPConfig


class AccountService:
    """Service for managing multiple email accounts.

    Provides a unified interface for accessing email accounts by their IDs.
    Handles credential retrieval and connector instantiation.
    """

    def __init__(
        self,
        accounts: list[AccountConfig],
        credentials: CredentialBackend,
    ) -> None:
        """Initialize the account service.

        Args:
            accounts: List of account configurations.
            credentials: Backend for retrieving account credentials.
        """
        self._accounts = {a.id: a for a in accounts}
        self._credentials = credentials

    def list_accounts(self) -> list[str]:
        """Return list of configured account IDs.

        Returns:
            List of account identifiers in the order they were configured.
        """
        return list(self._accounts.keys())

    def _create_connector(self, config: AccountConfig, password: SecretStr) -> BaseConnector:
        """Create a connector based on account configuration.

        Args:
            config: The account configuration.
            password: The account password.

        Returns:
            A configured connector instance.

        Raises:
            UnsupportedConnectorError: If the connector type is not supported.
        """
        if config.type == "imap":
            imap_config = IMAPConfig(
                host=config.host,
                port=config.port,
                username=config.username,
                password=password,
                ssl=config.ssl,
            )

            # Create SMTP config if send permission is enabled
            smtp_config = None
            if config.permissions.send:
                smtp_config = SMTPConfig(
                    host=config.smtp_host or config.host,
                    port=config.smtp_port,
                    username=config.username,
                    password=password,
                    ssl=config.smtp_ssl,
                )

            return IMAPConnector(imap_config, smtp_config=smtp_config)

        raise UnsupportedConnectorError(config.type)

    def get_mailbox(self, account_id: str) -> SecureMailbox:
        """Create SecureMailbox for the specified account.

        Args:
            account_id: The unique identifier of the account.

        Returns:
            A SecureMailbox instance configured for the account.

        Raises:
            AccountNotFoundError: If the account ID is not found.
            CredentialNotFoundError: If credentials cannot be retrieved.
            UnsupportedConnectorError: If the connector type is not supported.
        """
        config = self._accounts.get(account_id)
        if not config:
            raise AccountNotFoundError(account_id)

        password = self._credentials.get_password(account_id)
        connector = self._create_connector(config, password)

        # Build from_address with optional display name
        # Use config.from_address, fall back to config.username if not set
        base_address = config.from_address or config.username
        if config.from_name:
            from_address = f"{config.from_name} <{base_address}>"
        else:
            from_address = base_address

        return SecureMailbox(
            connector,
            config.permissions,
            from_address=from_address,
        )
