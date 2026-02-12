"""Account service for managing multiple email accounts."""

from pydantic import SecretStr

from read_no_evil_mcp.accounts.config import AccountConfig
from read_no_evil_mcp.accounts.credentials.base import CredentialBackend
from read_no_evil_mcp.defaults import DEFAULT_MAX_ATTACHMENT_SIZE
from read_no_evil_mcp.email.connectors.base import BaseConnector
from read_no_evil_mcp.email.connectors.config import IMAPConfig, SMTPConfig
from read_no_evil_mcp.email.connectors.imap import IMAPConnector
from read_no_evil_mcp.exceptions import AccountNotFoundError, UnsupportedConnectorError
from read_no_evil_mcp.filtering.access_rules import AccessRuleMatcher
from read_no_evil_mcp.mailbox import SecureMailbox


class AccountService:
    """Service for managing multiple email accounts.

    Provides a unified interface for accessing email accounts by their IDs.
    Handles credential retrieval and connector instantiation.
    """

    def __init__(
        self,
        accounts: list[AccountConfig],
        credentials: CredentialBackend,
        max_attachment_size: int = DEFAULT_MAX_ATTACHMENT_SIZE,
    ) -> None:
        """Initialize the account service.

        Args:
            accounts: List of account configurations.
            credentials: Backend for retrieving account credentials.
            max_attachment_size: Maximum attachment size in bytes.
        """
        self._accounts = {a.id: a for a in accounts}
        self._credentials = credentials
        self._max_attachment_size = max_attachment_size

    def list_accounts(self) -> list[str]:
        """Return list of configured account IDs.

        Returns:
            List of account identifiers in the order they were configured.
        """
        return list(self._accounts.keys())

    def get_config(self, account_id: str) -> AccountConfig:
        """Get the configuration for an account.

        Args:
            account_id: The unique identifier of the account.

        Returns:
            The account configuration.

        Raises:
            AccountNotFoundError: If the account ID is not found.
        """
        config = self._accounts.get(account_id)
        if not config:
            raise AccountNotFoundError(account_id)
        return config

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

        # Use config.from_address, fall back to config.username if not set
        from_address = config.from_address or config.username

        # Create access rules matcher if rules are configured
        access_rules_matcher = AccessRuleMatcher(
            sender_rules=config.sender_rules,
            subject_rules=config.subject_rules,
        )

        return SecureMailbox(
            connector,
            config.permissions,
            from_address=from_address,
            from_name=config.from_name,
            access_rules_matcher=access_rules_matcher,
            list_prompts=config.list_prompts or None,
            read_prompts=config.read_prompts or None,
            max_attachment_size=self._max_attachment_size,
        )
