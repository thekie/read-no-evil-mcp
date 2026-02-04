"""Environment variable credential backend."""

import os

from pydantic import SecretStr

from read_no_evil_mcp.accounts.credentials.base import CredentialBackend
from read_no_evil_mcp.exceptions import CredentialNotFoundError


class EnvCredentialBackend(CredentialBackend):
    """Credential backend using environment variables.

    Looks for passwords in environment variables named:
    RNOE_ACCOUNT_{ID}_PASSWORD

    Where {ID} is the account ID in uppercase with hyphens replaced by underscores.
    For example:
    - Account "work" -> RNOE_ACCOUNT_WORK_PASSWORD
    - Account "personal" -> RNOE_ACCOUNT_PERSONAL_PASSWORD
    - Account "my-gmail" -> RNOE_ACCOUNT_MY_GMAIL_PASSWORD
    """

    def get_password(self, account_id: str) -> SecretStr:
        """Retrieve password from environment variable.

        Args:
            account_id: The unique identifier of the account.

        Returns:
            The password as a SecretStr.

        Raises:
            CredentialNotFoundError: If the environment variable is not set.
        """
        # Normalize account ID: uppercase and replace hyphens with underscores
        normalized_id = account_id.upper().replace("-", "_")
        env_key = f"RNOE_ACCOUNT_{normalized_id}_PASSWORD"

        value = os.environ.get(env_key)
        if not value:
            raise CredentialNotFoundError(account_id, env_key)

        return SecretStr(value)
