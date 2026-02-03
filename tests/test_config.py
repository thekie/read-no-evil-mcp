"""Tests for configuration settings."""

import os
from unittest.mock import patch

import pytest

from read_no_evil_mcp.config import Settings


class TestSettings:
    def test_load_from_env(self):
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
        assert settings.imap_password.get_secret_value() == "secret123"
        assert settings.imap_ssl is True
        assert settings.default_lookback_days == 14

    def test_defaults(self):
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

    def test_ssl_false(self):
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

    def test_custom_port(self):
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

    def test_missing_required_raises(self):
        """Test that missing required fields raise an error."""
        from pydantic import ValidationError

        env = {
            "RNOE_IMAP_HOST": "imap.example.com",
            # Missing username and password
        }
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValidationError):
                Settings()

    def test_password_is_secret(self):
        """Test that password is stored as SecretStr."""
        env = {
            "RNOE_IMAP_HOST": "imap.example.com",
            "RNOE_IMAP_USERNAME": "user@example.com",
            "RNOE_IMAP_PASSWORD": "mysecret",
        }
        with patch.dict(os.environ, env, clear=False):
            settings = Settings()

        # Password value should not appear in string representation
        assert "mysecret" not in str(settings.imap_password)
        assert settings.imap_password.get_secret_value() == "mysecret"
