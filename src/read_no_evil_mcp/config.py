"""Configuration settings for read-no-evil-mcp using pydantic-settings."""

import os
from pathlib import Path
from typing import Any

from pydantic import Field, ValidationError, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from read_no_evil_mcp.accounts.config import AccountConfig
from read_no_evil_mcp.defaults import DEFAULT_MAX_ATTACHMENT_SIZE
from read_no_evil_mcp.exceptions import ConfigError
from read_no_evil_mcp.protection.models import ProtectionConfig


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
        """Read YAML config from file."""
        import yaml

        xdg_config = os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
        config_paths = [
            os.environ.get("RNOE_CONFIG_FILE"),
            Path.cwd() / "rnoe.yaml",
            Path(xdg_config) / "read-no-evil-mcp" / "config.yaml",
        ]

        for path in config_paths:
            if path and Path(path).exists():
                resolved = Path(path).resolve()
                try:
                    with open(resolved) as f:
                        data = yaml.safe_load(f)
                        return data if data else {}
                except yaml.YAMLError as e:
                    # Extract line info from YAML parse errors
                    location = ""
                    if hasattr(e, "problem_mark") and e.problem_mark is not None:
                        mark = e.problem_mark
                        location = f" at line {mark.line + 1}, column {mark.column + 1}"
                    problem = getattr(e, "problem", "invalid syntax")
                    raise ConfigError(
                        f"Configuration error: Invalid YAML syntax in "
                        f"{resolved}{location}: {problem}"
                    ) from e
                except PermissionError as e:
                    raise ConfigError(
                        f"Configuration error: Permission denied reading "
                        f"{resolved}. Check file permissions."
                    ) from e
                except OSError as e:
                    raise ConfigError(
                        f"Configuration error: Cannot read config file "
                        f"{resolved}: {e}"
                    ) from e

        return {}


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


def _format_validation_errors(e: ValidationError) -> str:
    """Convert Pydantic ValidationError into human-readable messages."""
    messages = []
    for error in e.errors():
        loc = " → ".join(str(part) for part in error["loc"]) if error["loc"] else "root"
        msg = error["msg"]
        err_type = error["type"]

        # Provide friendly messages for common error types
        if err_type == "missing":
            messages.append(f"  - '{loc}': required field is missing")
        elif err_type == "string_pattern_mismatch":
            if error["loc"] and error["loc"][-1] == "id":
                messages.append(
                    f"  - '{loc}': invalid format. "
                    f"Must start with a letter and contain only letters, "
                    f"numbers, hyphens, and underscores (e.g., 'work', 'my-gmail')"
                )
            else:
                messages.append(f"  - '{loc}': {msg}")
        else:
            messages.append(f"  - '{loc}': {msg}")

    return "Configuration error: invalid settings:\n" + "\n".join(messages)


def load_settings(**kwargs: Any) -> Settings:
    """Load and validate settings, converting errors to friendly ConfigError messages.

    This is the recommended way to create Settings instances. It catches
    Pydantic validation errors and re-raises them as readable ConfigError
    messages.

    Returns:
        Validated Settings instance.

    Raises:
        ConfigError: If configuration is invalid, with a human-readable message.
    """
    try:
        return Settings(**kwargs)
    except ConfigError:
        # Already a friendly error (e.g., from YAML parsing), re-raise as-is
        raise
    except ValidationError as e:
        raise ConfigError(_format_validation_errors(e)) from e
