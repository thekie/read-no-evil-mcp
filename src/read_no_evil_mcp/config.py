"""Configuration settings for read-no-evil-mcp using pydantic-settings."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables with RNOE_ prefix."""

    model_config = SettingsConfigDict(env_prefix="RNOE_")

    # IMAP configuration
    imap_host: str
    imap_port: int = 993
    imap_username: str
    imap_password: SecretStr
    imap_ssl: bool = True

    # Application defaults
    default_lookback_days: int = 7
