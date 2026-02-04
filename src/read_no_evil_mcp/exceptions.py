"""Custom exceptions for read-no-evil-mcp."""


class ReadNoEvilError(Exception):
    """Base exception for read-no-evil-mcp."""


class ConfigError(ReadNoEvilError):
    """Raised when there is a configuration error."""


class AccountNotFoundError(ReadNoEvilError):
    """Raised when a requested account is not found."""

    def __init__(self, account_id: str) -> None:
        self.account_id = account_id
        super().__init__(f"Account not found: {account_id}")


class CredentialNotFoundError(ConfigError):
    """Raised when credentials for an account are not found."""

    def __init__(self, account_id: str, env_key: str) -> None:
        self.account_id = account_id
        self.env_key = env_key
        super().__init__(
            f"Missing credential for account '{account_id}': "
            f"environment variable {env_key} is not set"
        )


class UnsupportedConnectorError(ConfigError):
    """Raised when an unsupported connector type is requested."""

    def __init__(self, connector_type: str) -> None:
        self.connector_type = connector_type
        super().__init__(f"Unsupported connector type: {connector_type}")


class PermissionDeniedError(ReadNoEvilError):
    """Raised when an operation is not permitted for an account."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
