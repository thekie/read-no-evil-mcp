"""Configuration settings for read-no-evil-mcp using pydantic-settings."""

import os
from pathlib import Path
from typing import Any

from pydantic import SecretStr
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from read_no_evil_mcp.accounts.config import AccountConfig


class YamlConfigSettingsSource(PydanticBaseSettingsSource):
    """Settings source that loads configuration from a YAML file.

    Looks for config file in the following order:
    1. RNOE_CONFIG_FILE environment variable
    2. ./rnoe.yaml (current directory)
    3. ~/.config/read-no-evil-mcp/config.yaml
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

        config_paths = [
            os.environ.get("RNOE_CONFIG_FILE"),
            Path.cwd() / "rnoe.yaml",
            Path.home() / ".config" / "read-no-evil-mcp" / "config.yaml",
        ]

        for path in config_paths:
            if path and Path(path).exists():
                with open(path) as f:
                    data = yaml.safe_load(f)
                    return data if data else {}

        return {}


class Settings(BaseSettings):
    """Application settings loaded from environment variables with RNOE_ prefix.

    Supports both legacy flat configuration (single account) and new multi-account
    configuration via YAML file.

    Environment variables (legacy single account):
        RNOE_IMAP_HOST, RNOE_IMAP_PORT, RNOE_IMAP_USERNAME, RNOE_IMAP_PASSWORD, etc.

    YAML configuration (multi-account):
        accounts:
          - id: "work"
            type: "imap"
            host: "mail.company.com"
            username: "user@company.com"

    Account passwords are always retrieved via credential backends
    (e.g., RNOE_ACCOUNT_WORK_PASSWORD environment variable).
    """

    model_config = SettingsConfigDict(env_prefix="RNOE_")

    # Multi-account configuration (preferred)
    accounts: list[AccountConfig] = []

    # Legacy IMAP configuration (single account, for backwards compatibility)
    imap_host: str | None = None
    imap_port: int = 993
    imap_username: str | None = None
    imap_password: SecretStr | None = None
    imap_ssl: bool = True

    # Application defaults
    default_lookback_days: int = 7

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

    def get_effective_accounts(self) -> list[AccountConfig]:
        """Get list of configured accounts, including legacy account if set.

        If multi-account configuration is provided, use that.
        Otherwise, if legacy single-account environment variables are set,
        create a default account from them.

        Returns:
            List of AccountConfig objects.
        """
        if self.accounts:
            return self.accounts

        # Fall back to legacy single-account configuration
        if self.imap_host and self.imap_username:
            return [
                AccountConfig(
                    id="default",
                    type="imap",
                    host=self.imap_host,
                    port=self.imap_port,
                    username=self.imap_username,
                    ssl=self.imap_ssl,
                )
            ]

        return []
