"""Tests for configuration settings."""

import os
from unittest.mock import patch

from read_no_evil_mcp.config import Settings


class TestSettings:
    def test_load_from_env(self) -> None:
        """Test loading settings from environment variables."""
        env = {
            "RNOE_IMAP_HOST": "imap.example.com",
            "RNOE_IMAP_PORT": "993",
            "RNOE_IMAP_USERNAME": "user@example.com",
            "RNOE_IMAP_PASSWORD": "secret123",
            "RNOE_IMAP_SSL": "true",
            "RNOE_DEFAULT_LOOKBACK_DAYS": "14",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = Settings()

        assert settings.imap_host == "imap.example.com"
        assert settings.imap_port == 993
        assert settings.imap_username == "user@example.com"
        assert settings.imap_password is not None
        assert settings.imap_password.get_secret_value() == "secret123"
        assert settings.imap_ssl is True
        assert settings.default_lookback_days == 14

    def test_defaults(self) -> None:
        """Test default values for optional settings."""
        env = {
            "RNOE_IMAP_HOST": "imap.example.com",
            "RNOE_IMAP_USERNAME": "user@example.com",
            "RNOE_IMAP_PASSWORD": "secret123",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = Settings()

        assert settings.imap_port == 993
        assert settings.imap_ssl is True
        assert settings.default_lookback_days == 7

    def test_ssl_false(self) -> None:
        """Test setting SSL to false."""
        env = {
            "RNOE_IMAP_HOST": "imap.example.com",
            "RNOE_IMAP_USERNAME": "user@example.com",
            "RNOE_IMAP_PASSWORD": "secret123",
            "RNOE_IMAP_SSL": "false",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = Settings()

        assert settings.imap_ssl is False

    def test_custom_port(self) -> None:
        """Test custom port setting."""
        env = {
            "RNOE_IMAP_HOST": "imap.example.com",
            "RNOE_IMAP_PORT": "143",
            "RNOE_IMAP_USERNAME": "user@example.com",
            "RNOE_IMAP_PASSWORD": "secret123",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = Settings()

        assert settings.imap_port == 143

    def test_no_config_no_error(self) -> None:
        """Test that settings can be created without any config (accounts will be empty)."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()

        assert settings.imap_host is None
        assert settings.imap_username is None
        assert settings.imap_password is None
        assert settings.accounts == []

    def test_password_is_secret(self) -> None:
        """Test that password is stored as SecretStr."""
        env = {
            "RNOE_IMAP_HOST": "imap.example.com",
            "RNOE_IMAP_USERNAME": "user@example.com",
            "RNOE_IMAP_PASSWORD": "mysecret",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = Settings()

        # Password value should not appear in string representation
        assert settings.imap_password is not None
        assert "mysecret" not in str(settings.imap_password)
        assert settings.imap_password.get_secret_value() == "mysecret"


class TestGetEffectiveAccounts:
    def test_legacy_config_creates_default_account(self) -> None:
        """Test that legacy config creates a 'default' account."""
        env = {
            "RNOE_IMAP_HOST": "imap.example.com",
            "RNOE_IMAP_USERNAME": "user@example.com",
            "RNOE_IMAP_PASSWORD": "secret123",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = Settings()

        accounts = settings.get_effective_accounts()

        assert len(accounts) == 1
        assert accounts[0].id == "default"
        assert accounts[0].host == "imap.example.com"
        assert accounts[0].username == "user@example.com"

    def test_no_config_returns_empty_list(self) -> None:
        """Test that no config returns empty list."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()

        accounts = settings.get_effective_accounts()

        assert accounts == []

    def test_partial_legacy_config_returns_empty_list(self) -> None:
        """Test partial legacy config (missing host or username) returns empty."""
        env = {
            "RNOE_IMAP_HOST": "imap.example.com",
            # Missing username
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()

        accounts = settings.get_effective_accounts()

        assert accounts == []

    def test_legacy_config_uses_settings_values(self) -> None:
        """Test legacy account config uses all settings values."""
        env = {
            "RNOE_IMAP_HOST": "imap.example.com",
            "RNOE_IMAP_PORT": "143",
            "RNOE_IMAP_USERNAME": "user@example.com",
            "RNOE_IMAP_PASSWORD": "secret",
            "RNOE_IMAP_SSL": "false",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = Settings()

        accounts = settings.get_effective_accounts()

        assert len(accounts) == 1
        assert accounts[0].port == 143
        assert accounts[0].ssl is False
