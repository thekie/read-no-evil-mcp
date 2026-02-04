"""Abstract base class for credential backends."""

from abc import ABC, abstractmethod

from pydantic import SecretStr


class CredentialBackend(ABC):
    """Abstract interface for credential storage.

    Credential backends are responsible for retrieving passwords for email accounts.
    Different implementations can retrieve credentials from environment variables,
    keyrings, encrypted files, etc.
    """

    @abstractmethod
    def get_password(self, account_id: str) -> SecretStr:
        """Retrieve password for the given account.

        Args:
            account_id: The unique identifier of the account.

        Returns:
            The password as a SecretStr.

        Raises:
            CredentialNotFoundError: If the credential is not found.
        """
        ...
