"""Environment variable credential backend."""

import logging
import os
import re

from pydantic import SecretStr

from read_no_evil_mcp.accounts.credentials.base import CredentialBackend
from read_no_evil_mcp.exceptions import CredentialNotFoundError

logger = logging.getLogger(__name__)


def normalize_account_id(account_id: str) -> str:
    """Normalize an account ID for use in environment variable names.

    Replaces non-alphanumeric characters with underscores and uppercases the result.

    For example:
    - "work" -> "WORK"
    - "my-gmail" -> "MY_GMAIL"
    - "user@example.com" -> "USER_EXAMPLE_COM"
    """
    return re.sub(r"[^a-zA-Z0-9]", "_", account_id).upper()


class EnvCredentialBackend(CredentialBackend):
    """Credential backend using environment variables.

    Looks for passwords in environment variables named:
    RNOE_ACCOUNT_{ID}_PASSWORD

    Where {ID} is the normalized account ID (uppercased, non-alphanumeric replaced
    with underscores).
    For example:
    - Account "work" -> RNOE_ACCOUNT_WORK_PASSWORD
    - Account "my-gmail" -> RNOE_ACCOUNT_MY_GMAIL_PASSWORD
    - Account "user@example.com" -> RNOE_ACCOUNT_USER_EXAMPLE_COM_PASSWORD
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
        normalized_id = normalize_account_id(account_id)
        env_key = f"RNOE_ACCOUNT_{normalized_id}_PASSWORD"

        logger.debug("Looking up password (env_key=%s)", env_key)

        value = os.environ.get(env_key)
        if not value:
            raise CredentialNotFoundError(account_id, env_key)

        return SecretStr(value)
