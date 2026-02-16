"""Configuration settings for read-no-evil-mcp using pydantic-settings."""

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field, field_validator
from pydantic_core import ValidationError
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from read_no_evil_mcp.accounts.config import AccountConfig
from read_no_evil_mcp.defaults import DEFAULT_MAX_ATTACHMENT_SIZE
from read_no_evil_mcp.protection.models import ProtectionConfig


class ConfigError(Exception):
    """Custom exception for configuration errors with user-friendly messages."""

    def __init__(self, message: str, file_path: str | None = None, line: int | None = None, col: int | None = None):
        self.file_path = file_path
        self.line = line
        self.col = col
        full_message = message
        if file_path:
            location = f" in {file_path}"
            if line is not None:
                location += f" at line {line}"
                if col is not None:
                    location += f", column {col}"
            full_message = f"Configuration error{location}: {message}"
        super().__init__(full_message)


class YamlConfigSettingsSource(PydanticBaseSettingsSource):
    """Settings source that loads configuration from a YAML file.

    Looks for config file in the following order:
    1. RNOE_CONFIG_FILE environment variable
    2. ./rnoe.yaml (current directory)
    3. $XDG_CONFIG_HOME/read-no-evil-mcp/config.yaml (defaults to ~/.config)
    """

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        """Get field value from YAML config."""
        yaml_data = self._load_yaml_config()
        field_value = yaml_data.get(field_name)
        return field_value, field_name, False

    def __call__(self) -> dict[str, Any]:
        """Return all settings from YAML config."""
        return self._load_yaml_config()

    def _load_yaml_config(self) -> dict[str, Any]:
        """Load and cache YAML config file."""
        if not hasattr(self, "_yaml_data"):
            self._yaml_data = self._read_yaml_file()
        return self._yaml_data

    def _read_yaml_file(self) -> dict[str, Any]:
        """Read YAML config from file with improved error messages."""
        xdg_config = os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
        config_paths = [
            os.environ.get("RNOE_CONFIG_FILE"),
            Path.cwd() / "rnoe.yaml",
            Path(xdg_config) / "read-no-evil-mcp" / "config.yaml",
        ]

        for path in config_paths:
            if path:
                path_obj = Path(path)
                if path_obj.exists():
                    try:
                        with open(path_obj) as f:
                            data = yaml.safe_load(f)
                            return data if data else {}
                    except yaml.YAMLError as e:
                        # Parse YAML error location if available
                        line = getattr(e, 'problem_mark', None)
                        line_num = line.line if line else None
                        col_num = line.column if line else None
                        error_msg = str(e)
                        if hasattr(e, 'problem'):
                            error_msg = e.problem
                        raise ConfigError(
                            f"Invalid YAML syntax: {error_msg}",
                            file_path=str(path_obj),
                            line=line_num,
                            col=col_num,
                        ) from e
                    except PermissionError as e:
                        raise ConfigError(
                            f"Cannot read config file — permission denied",
                            file_path=str(path_obj),
                        ) from e
                    except OSError as e:
                        raise ConfigError(
                            f"Cannot read config file: {e}",
                            file_path=str(path_obj),
                        ) from e

        return {}


def _parse_validation_error(error: ValidationError, accounts: list[dict] | None = None) -> str:
    """Convert Pydantic ValidationError to user-friendly message."""
    errors = error.errors()
    if not errors:
        return "Unknown validation error"

    # Group errors by location
    for err in errors:
        loc = err.get("loc", ())
        msg = err.get("msg", "")
        input_type = err.get("type", "")

        # Check for missing required fields (especially for accounts)
        if input_type == "missing" and loc:
            field_name = loc[-1]
            # Check if this is an account configuration
            if "account" in [str(l).lower() for l in loc] or (accounts and any(
                field_name in ["host", "username", "password"] for acc in accounts
            )):
                if field_name == "host":
                    return f"Account is missing required field 'host'. Required fields for IMAP accounts: host, username"
                elif field_name == "username":
                    return f"Account is missing required field 'username'. Required fields for IMAP accounts: host, username"
                elif field_name == "id":
                    return "Account is missing required field 'id'. Each account needs a unique identifier (e.g., 'work', 'personal')"
            return f"Missing required field '{field_name}'"

        # Check for invalid account ID format
        if input_type == "string_pattern" and "id" in [str(l).lower() for l in loc]:
            return "Account ID must start with a letter and contain only letters, numbers, hyphens, and underscores (e.g., 'work', 'my-gmail')"

        # Generic field errors
        if loc:
            field_name = ".".join(str(l) for l in loc)
            return f"Invalid value for '{field_name}': {msg}"

    return str(error)


class Settings(BaseSettings):
    """Application settings loaded from environment variables with RNOE_ prefix.

    Multi-account configuration via YAML file:
        accounts:
          - id: "work"
            type: "imap"
            host: "mail.company.com"
            username: "user@company.com"

    Account passwords are retrieved via credential backends
    (e.g., RNOE_ACCOUNT_WORK_PASSWORD environment variable).
    """

    model_config = SettingsConfigDict(env_prefix="RNOE_")

    # Multi-account configuration
    accounts: list[AccountConfig] = []

    # Protection settings
    protection: ProtectionConfig = Field(default_factory=ProtectionConfig)

    # Application defaults
    default_lookback_days: int = 7
    max_attachment_size: int = DEFAULT_MAX_ATTACHMENT_SIZE

    @field_validator("max_attachment_size")
    @classmethod
    def _validate_max_attachment_size(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("max_attachment_size must be positive")
        return v

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Customize settings sources to include YAML config."""
        return (
            init_settings,
            env_settings,
            YamlConfigSettingsSource(settings_cls),
            dotenv_settings,
            file_secret_settings,
        )


def get_settings_eager() -> Settings:
    """Load settings with eager validation at startup.
    
    This function validates configuration immediately, failing fast with
    clear error messages if the configuration is invalid.
    
    Raises:
        ConfigError: If configuration is invalid with user-friendly message.
        ValidationError: If Pydantic validation fails (wrapped message).
    """
    try:
        settings = Settings()
        # Validate accounts by accessing them (triggers any lazy validation)
        _ = settings.accounts
        _ = settings.protection
        return settings
    except ValidationError as e:
        # Convert to user-friendly message
        friendly_msg = _parse_validation_error(e)
        raise ConfigError(friendly_msg) from e
